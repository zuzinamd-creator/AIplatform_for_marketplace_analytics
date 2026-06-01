"""
Inventory rebuild scalability benchmark (PostgreSQL + streaming replay).

Requires:
  RUN_INTEGRATION_TESTS=true
  RUN_STRESS_TESTS=true
  alembic upgrade head on TEST_DATABASE_URL

Run:
  pytest tests/integration/test_inventory_rebuild_benchmark.py -v -s
"""

from __future__ import annotations

import os
import tracemalloc
from dataclasses import dataclass
from time import perf_counter

import pytest
from app.core.security_context import TenantSession
from app.domain.inventory.snapshot_fingerprint import fingerprint_from_model
from app.etl.wb.full_inventory_rebuild import FullInventoryRebuildService
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.models.inventory import InventoryLedgerEntry, WarehouseStockSnapshot
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.inventory_scale_fixtures import (
    ScaleTenantSeed,
    build_scale_spec,
    seed_scale_tenant,
    stream_ledger_group_stats,
)
from tests.integration.rebuild_helpers import run_full_rebuild_timed


def _stress_enabled() -> bool:
    return os.getenv("RUN_STRESS_TESTS", "false").lower() == "true"


def _mb(num_bytes: int) -> float:
    return num_bytes / (1024 * 1024)


@dataclass(frozen=True)
class WalObservation:
    wal_bytes: int | None
    wal_records: int | None


@dataclass(frozen=True)
class RebuildBenchmarkMetrics:
    ledger_rows: int
    sku_count: int
    warehouse_count: int
    stream_groups: int
    max_rows_per_group: int
    stream_peak_mb: float
    stream_wall_ms: float
    full_rebuild_ms: float
    full_rows_per_sec: float
    snapshot_rows: int
    incremental_rebuild_ms: float
    lock_hold_ms: float
    wal_before: WalObservation
    wal_after_full: WalObservation
    fingerprints_stable_on_replay: bool
    full_incremental_equivalent: bool

    def format_report(self) -> str:
        wal_delta = None
        if self.wal_before.wal_bytes is not None and self.wal_after_full.wal_bytes is not None:
            wal_delta = self.wal_after_full.wal_bytes - self.wal_before.wal_bytes
        lines = [
            "=== Inventory rebuild scalability benchmark ===",
            f"ledger_rows: {self.ledger_rows:,}",
            f"sku_count: {self.sku_count}, warehouses: {self.warehouse_count}",
            f"stream_groups: {self.stream_groups:,}, max_rows_per_group: {self.max_rows_per_group}",
            (
                f"stream replay peak RAM: {self.stream_peak_mb:.2f} MiB "
                "(grouped server-side cursor; not full-ledger heap)"
            ),
            f"stream-only wall time: {self.stream_wall_ms:.1f} ms",
            f"full rebuild: {self.full_rebuild_ms:.1f} ms ({self.full_rows_per_sec:,.0f} ledger rows/s)",
            f"snapshot_rows: {self.snapshot_rows:,}",
            f"incremental rebuild (full window): {self.incremental_rebuild_ms:.1f} ms",
            f"advisory lock + second full rebuild txn: {self.lock_hold_ms:.1f} ms",
            (
                f"WAL bytes (pg_stat_wal cumulative): before={self.wal_before.wal_bytes}, "
                f"after_full={self.wal_after_full.wal_bytes}, delta={wal_delta}"
            ),
            f"deterministic replay (2x full): {self.fingerprints_stable_on_replay}",
            f"full vs incremental equivalence: {self.full_incremental_equivalent}",
        ]
        return "\n".join(lines)


async def _read_wal_stats(session: AsyncSession) -> WalObservation:
    result = await session.execute(text("SELECT wal_bytes, wal_records FROM pg_stat_wal"))
    row = result.one_or_none()
    if row is None:
        return WalObservation(wal_bytes=None, wal_records=None)
    return WalObservation(wal_bytes=int(row[0]), wal_records=int(row[1]))


async def _snapshot_fingerprint_map(
    session: AsyncSession,
    user_id,
) -> dict[tuple, str]:
    result = await session.execute(
        select(WarehouseStockSnapshot).where(WarehouseStockSnapshot.user_id == user_id)
    )
    return {
        (row.snapshot_date, row.sku, row.warehouse_name): fingerprint_from_model(row)
        for row in result.scalars().all()
    }


async def _delete_all_snapshots(session: AsyncSession, user_id) -> None:
    await session.execute(
        delete(WarehouseStockSnapshot).where(WarehouseStockSnapshot.user_id == user_id)
    )


@pytest.fixture
def scale_spec():
    if not _stress_enabled():
        pytest.skip("Set RUN_STRESS_TESTS=true to run inventory rebuild benchmarks")
    custom = os.getenv("SCALE_LEDGER_ROWS")
    rows = int(custom) if custom else 52_000
    return build_scale_spec(ledger_rows=rows)


@pytest.fixture
async def scale_tenant(
    session_factory,
    scale_spec,
) -> ScaleTenantSeed:
    if not _stress_enabled():
        pytest.skip("Set RUN_STRESS_TESTS=true to run inventory rebuild benchmarks")
    return await seed_scale_tenant(session_factory, scale_spec)


@pytest.mark.integration
async def test_inventory_rebuild_scalability_benchmark(
    session_factory,
    scale_tenant: ScaleTenantSeed,
) -> None:
    user_id = scale_tenant.user_id
    spec = scale_tenant.spec

    async with session_factory() as session:
        wal_before = await _read_wal_stats(session)

    tracemalloc.start()
    stream_started = perf_counter()
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            ledger_rows, stream_groups, max_group = await stream_ledger_group_stats(
                session, user_id
            )
    stream_wall_ms = (perf_counter() - stream_started) * 1000
    _current, stream_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert ledger_rows == spec.ledger_rows
    assert stream_groups == spec.sku_count * spec.warehouse_count
    assert max_group == spec.days_span
    assert stream_peak < 256 * 1024 * 1024, "streaming peak RAM should stay bounded (<256 MiB)"

    full_timing = await run_full_rebuild_timed(session_factory, user_id)
    full_rows_per_sec = (
        spec.ledger_rows / (full_timing.duration_ms / 1000) if full_timing.duration_ms > 0 else 0
    )

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            fingerprints_first = await _snapshot_fingerprint_map(session, user_id)

    lock_started = perf_counter()
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            await FullInventoryRebuildService(session, user_id).rebuild()
            fingerprints_second = await _snapshot_fingerprint_map(session, user_id)
    lock_hold_ms = (perf_counter() - lock_started) * 1000

    fingerprints_stable = fingerprints_first == fingerprints_second
    assert fingerprints_stable, "full rebuild must be deterministic for the same ledger"

    async with session_factory() as session:
        wal_after_full = await _read_wal_stats(session)

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            min_date = (
                await session.execute(
                    select(func.min(InventoryLedgerEntry.operation_date)).where(
                        InventoryLedgerEntry.user_id == user_id
                    )
                )
            ).scalar_one()
            await _delete_all_snapshots(session, user_id)
            inc_started = perf_counter()
            await InventorySnapshotRebuildService(session, user_id).rebuild(
                earliest_affected_date=min_date,
            )
            fingerprints_incremental = await _snapshot_fingerprint_map(session, user_id)
    incremental_ms = (perf_counter() - inc_started) * 1000

    full_incremental_equivalent = fingerprints_first == fingerprints_incremental
    assert full_incremental_equivalent, "incremental full-window must match full rebuild fingerprints"

    metrics = RebuildBenchmarkMetrics(
        ledger_rows=spec.ledger_rows,
        sku_count=spec.sku_count,
        warehouse_count=spec.warehouse_count,
        stream_groups=stream_groups,
        max_rows_per_group=max_group,
        stream_peak_mb=_mb(stream_peak),
        stream_wall_ms=stream_wall_ms,
        full_rebuild_ms=full_timing.duration_ms,
        full_rows_per_sec=full_rows_per_sec,
        snapshot_rows=full_timing.row_count,
        incremental_rebuild_ms=incremental_ms,
        lock_hold_ms=lock_hold_ms,
        wal_before=wal_before,
        wal_after_full=wal_after_full,
        fingerprints_stable_on_replay=fingerprints_stable,
        full_incremental_equivalent=full_incremental_equivalent,
    )
    print(metrics.format_report())

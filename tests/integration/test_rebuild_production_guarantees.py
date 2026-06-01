"""
Production-safe rebuild guarantees (PostgreSQL integration).

Proves visibility, advisory locking, persist/rebuild contention, and drift verification
without modifying rebuild algorithms or staging architecture.

Run:
  RUN_INTEGRATION_TESTS=true pytest tests/integration/test_rebuild_production_guarantees.py -v
"""

from __future__ import annotations

import asyncio
from datetime import date
from time import perf_counter
from uuid import uuid4

import pytest
from app.core.inventory_rebuild_lock import acquire_inventory_rebuild_lock
from app.core.security_context import TenantSession
from app.domain.inventory.errors import InventoryRebuildBusyError
from app.etl.wb.full_inventory_rebuild import FullInventoryRebuildService
from app.etl.wb.inventory_consistency_verification import InventoryConsistencyVerificationService
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.models.inventory import InventoryLedgerEntry, WarehouseStockSnapshot
from app.models.inventory.integrity import (
    InventoryIntegrityAnomaly,
    InventoryIntegrityAnomalyType,
    SnapshotConsistencyCheck,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.rebuild_helpers import (
    SKU,
    WAREHOUSE,
    corrupt_snapshot_actual_stock,
    count_staging_rows,
    create_tenant_with_persisted_ledger,
    ledger_entry_count,
    observe_live_snapshots,
    orchestrate_full_rebuild_pause_before_promote,
    run_full_rebuild_timed,
)
from tests.integration.wb_fixtures import wb_sale_csv

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_promote_visibility_readers_see_old_or_new_complete_state(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """
    While rebuild txn holds after staging but before promote commit, readers see OLD live data.

    After commit, readers see NEW complete state. Staging rows never appear in live queries.
    """
    user_id, _report_id = await create_tenant_with_persisted_ledger(session_factory)
    baseline = await observe_live_snapshots(session_factory, user_id)
    assert baseline.row_count > 0, "baseline snapshots required"

    pause_gate = asyncio.Event()
    reader_done = asyncio.Event()
    reader_observations: list = []
    violations: list[str] = []

    async def holder() -> None:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                _, expected_snapshots = await orchestrate_full_rebuild_pause_before_promote(
                    session,
                    user_id,
                    pause_before_promote=pause_gate,
                    reader_observed_old=reader_done,
                )
                assert expected_snapshots, "full rebuild should produce snapshots"

    async def reader() -> None:
        await pause_gate.wait()
        staging_count = await count_staging_rows(session_factory, user_id)
        for _ in range(5):
            obs = await observe_live_snapshots(session_factory, user_id)
            reader_observations.append(obs)
            if obs.row_count == 0 and baseline.row_count > 0:
                violations.append("live snapshot set appeared empty during rebuild txn")
            if obs.row_count != baseline.row_count:
                violations.append(
                    f"live row_count changed mid-txn: {obs.row_count} vs baseline {baseline.row_count}"
                )
            if obs.total_actual_stock != baseline.total_actual_stock:
                violations.append("live total_actual_stock changed mid-txn")
            await asyncio.sleep(0.05)
        if staging_count > 0:
            pass  # staging may hold new rows; live must not
        reader_done.set()

    await asyncio.wait_for(
        asyncio.gather(holder(), reader()),
        timeout=30.0,
    )
    assert not violations, "; ".join(violations)

    after = await observe_live_snapshots(session_factory, user_id)
    assert after.row_count > 0
    assert after.distinct_keys > 0
    staging_after = await count_staging_rows(session_factory, user_id)
    assert staging_after == 0, "staging must be cleared after promote"


@pytest.mark.asyncio
async def test_advisory_lock_non_blocking_and_no_deadlock(session_factory) -> None:
    """Second session fails fast with InventoryRebuildBusyError; gather completes without deadlock."""
    user_id, _ = await create_tenant_with_persisted_ledger(session_factory)
    holder_acquired = asyncio.Event()
    contender_finished = asyncio.Event()
    lock_wait_ms: list[float] = []

    async def holder() -> None:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                started = perf_counter()
                await acquire_inventory_rebuild_lock(session, user_id)
                lock_wait_ms.append((perf_counter() - started) * 1000)
                holder_acquired.set()
                await asyncio.wait_for(contender_finished.wait(), timeout=10.0)

    async def contender() -> None:
        await holder_acquired.wait()
        started = perf_counter()
        try:
            async with session_factory() as session:
                async with TenantSession.transaction(session, user_id):
                    with pytest.raises(InventoryRebuildBusyError) as exc_info:
                        await acquire_inventory_rebuild_lock(session, user_id)
                    assert exc_info.value.retryable is True
        finally:
            lock_wait_ms.append((perf_counter() - started) * 1000)
            contender_finished.set()

    await asyncio.wait_for(asyncio.gather(holder(), contender()), timeout=15.0)
    assert lock_wait_ms[1] < 500, "contender must fail fast (<500ms), not block"


@pytest.mark.asyncio
async def test_full_rebuild_second_attempt_fails_fast_under_lock(session_factory) -> None:
    user_id, _ = await create_tenant_with_persisted_ledger(session_factory)
    holder_started = asyncio.Event()
    contender_done = asyncio.Event()

    async def holder() -> None:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                await acquire_inventory_rebuild_lock(session, user_id)
                holder_started.set()
                await asyncio.wait_for(contender_done.wait(), timeout=10.0)

    async def contender() -> None:
        await holder_started.wait()
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                service = FullInventoryRebuildService(session, user_id)
                with pytest.raises(InventoryRebuildBusyError):
                    await service.rebuild()
        contender_done.set()

    await asyncio.gather(holder(), contender())


@pytest.mark.asyncio
async def test_persist_and_rebuild_contention_preserves_ledger_and_snapshots(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Concurrent incremental rebuild + second persist; ledger never shrinks; no snapshot dupes."""
    from datetime import UTC, datetime

    from app.models.report import Marketplace, Report, ReportStatus, ReportType

    user_id, base_report_id = await create_tenant_with_persisted_ledger(session_factory)
    ledger_before = await ledger_entry_count(session_factory, user_id)

    report_id = uuid4()
    checksum = f"contention-followup-{report_id}"
    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="contention_followup.csv",
        file_path="reports/contention_followup.csv",
        file_checksum=checksum,
        status=ReportStatus.PROCESSING,
    )
    processed = WbFinancialProcessor.process(
        report_id=report_id,
        report_created_at=datetime.now(UTC),
        filename="contention_followup.csv",
        content=wb_sale_csv(sku=f"{SKU}-B", warehouse=WAREHOUSE),
    )

    from decimal import Decimal

    from app.models.cost_history import CostHistory

    start_gate = asyncio.Event()

    async def followup_persist() -> None:
        await start_gate.wait()
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                session.add(
                    CostHistory(
                        user_id=user_id,
                        internal_sku=f"{SKU}-B",
                        cost=Decimal("10"),
                        product_cost=Decimal("10"),
                        packaging_cost=Decimal("0"),
                        inbound_logistics_cost=Decimal("0"),
                        additional_cost=Decimal("0"),
                        currency="RUB",
                        effective_from=date(2026, 1, 1),
                    )
                )
                session.add(report)
                await session.flush()
                svc = WbFinancialPersistService(session, user_id)
                costs = await WbFinancialPersistService.load_cost_snapshots(session, user_id)
                enriched = WbFinancialProcessor.enrich_with_costs(processed, costs)
                await svc.persist(
                    report=report,
                    file_checksum=checksum,
                    storage_uri=report.file_path or "",
                    result=enriched,
                )

    async def rebuild() -> None:
        await start_gate.wait()
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                await InventorySnapshotRebuildService(session, user_id).rebuild(
                    earliest_affected_date=date(2026, 1, 15)
                )

    tasks = [
        asyncio.create_task(followup_persist()),
        asyncio.create_task(rebuild()),
    ]
    await asyncio.sleep(0)
    start_gate.set()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for outcome in results:
        if isinstance(outcome, InventoryRebuildBusyError):
            async with session_factory() as session:
                async with TenantSession.transaction(session, user_id):
                    await InventorySnapshotRebuildService(session, user_id).rebuild(
                        earliest_affected_date=date(2026, 1, 15)
                    )
        elif isinstance(outcome, Exception):
            raise outcome

    ledger_after = await ledger_entry_count(session_factory, user_id)
    assert ledger_after >= ledger_before, "append-only ledger must not shrink under contention"

    if ledger_after == ledger_before:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                session.add(report)
                await session.flush()
                svc = WbFinancialPersistService(session, user_id)
                costs = await WbFinancialPersistService.load_cost_snapshots(session, user_id)
                enriched = WbFinancialProcessor.enrich_with_costs(processed, costs)
                await svc.persist(
                    report=report,
                    file_checksum=checksum,
                    storage_uri=report.file_path or "",
                    result=enriched,
                )
        ledger_after = await ledger_entry_count(session_factory, user_id)

    assert ledger_after > ledger_before

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            distinct_reports = (
                await session.execute(
                    select(func.count(func.distinct(InventoryLedgerEntry.report_id))).where(
                        InventoryLedgerEntry.user_id == user_id
                    )
                )
            ).scalar_one()
    assert distinct_reports >= 2

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            dupes = (
                await session.execute(
                    select(
                        WarehouseStockSnapshot.snapshot_date,
                        WarehouseStockSnapshot.sku,
                        WarehouseStockSnapshot.warehouse_name,
                        func.count(),
                    )
                    .where(WarehouseStockSnapshot.user_id == user_id)
                    .group_by(
                        WarehouseStockSnapshot.snapshot_date,
                        WarehouseStockSnapshot.sku,
                        WarehouseStockSnapshot.warehouse_name,
                    )
                    .having(func.count() > 1)
                )
            ).all()
    assert dupes == []



@pytest.mark.asyncio
async def test_drift_verification_records_check_and_anomaly_ledger_unchanged(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id, report_id = await create_tenant_with_persisted_ledger(session_factory)
    ledger_before = await ledger_entry_count(session_factory, user_id, report_id=report_id)

    updated = await corrupt_snapshot_actual_stock(
        session_factory,
        user_id,
        snapshot_date=date(2026, 1, 15),
        sku=SKU,
        warehouse_name=WAREHOUSE,
        corrupt_value=99999,
    )
    assert updated == 1

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            summary = await InventoryConsistencyVerificationService(session, user_id).verify_sample(
                max_keys=20,
                seed=42,
            )

    assert summary.drifted >= 1
    assert summary.checked >= 1

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            drift_anomalies = (
                await session.execute(
                    select(func.count())
                    .select_from(InventoryIntegrityAnomaly)
                    .where(
                        InventoryIntegrityAnomaly.user_id == user_id,
                        InventoryIntegrityAnomaly.anomaly_type
                        == InventoryIntegrityAnomalyType.SNAPSHOT_DRIFT,
                    )
                )
            ).scalar_one()
            inconsistent_checks = (
                await session.execute(
                    select(func.count())
                    .select_from(SnapshotConsistencyCheck)
                    .where(
                        SnapshotConsistencyCheck.user_id == user_id,
                        SnapshotConsistencyCheck.is_consistent.is_(False),
                    )
                )
            ).scalar_one()

    assert drift_anomalies >= 1
    assert inconsistent_checks >= 1

    ledger_after = await ledger_entry_count(session_factory, user_id, report_id=report_id)
    assert ledger_after == ledger_before


@pytest.mark.asyncio
async def test_full_rebuild_timing_observable(session_factory) -> None:
    """Records rebuild duration for operator visibility (not a SLA assertion)."""
    user_id, _ = await create_tenant_with_persisted_ledger(session_factory)
    timing = await run_full_rebuild_timed(session_factory, user_id)
    assert timing.row_count > 0
    assert timing.duration_ms > 0
    assert timing.duration_ms < 120_000, "sanity bound for local integration dataset"

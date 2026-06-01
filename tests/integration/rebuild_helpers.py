"""Shared helpers for rebuild production-guarantee integration tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from time import perf_counter
from uuid import UUID, uuid4

from app.core.inventory_rebuild_lock import acquire_inventory_rebuild_lock
from app.core.security_context import TenantSession
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.etl.wb.full_inventory_rebuild import FullInventoryRebuildService
from app.etl.wb.inventory_ledger_streaming import InventoryLedgerStreamingService
from app.etl.wb.inventory_snapshot_compute import InventorySnapshotComputeService
from app.etl.wb.inventory_snapshot_store import InventorySnapshotStore
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry, WarehouseStockSnapshot
from app.models.inventory.staging import WarehouseStockSnapshotStaging
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.integration.wb_fixtures import wb_sale_csv

SKU = "SKU-REBUILD-GUARANTEE"
WAREHOUSE = "Коледино"


@dataclass(frozen=True)
class LiveSnapshotObservation:
    row_count: int
    total_actual_stock: int
    distinct_keys: int


@dataclass(frozen=True)
class RebuildTiming:
    duration_ms: float
    row_count: int


async def create_tenant_with_persisted_ledger(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID]:
    """Seed user, cost, WB CSV persist (ledger + incremental snapshots)."""
    user_id = uuid4()
    report_id = uuid4()
    checksum = f"rebuild-guarantee-{report_id}"
    user = User(
        id=user_id,
        email=f"rebuild-{user_id}@example.com",
        hashed_password="test",
        is_active=True,
    )
    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="rebuild_guarantee.csv",
        file_path="reports/rebuild_guarantee.csv",
        file_checksum=checksum,
        status=ReportStatus.PROCESSING,
    )
    processed = WbFinancialProcessor.process(
        report_id=report_id,
        report_created_at=datetime.now(UTC),
        filename="rebuild_guarantee.csv",
        content=wb_sale_csv(sku=SKU, warehouse=WAREHOUSE),
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
        async with TenantSession.transaction(session, user_id):
            session.add(report)
            session.add(
                CostHistory(
                    user_id=user_id,
                    internal_sku=SKU,
                    cost=Decimal("10"),
                    product_cost=Decimal("10"),
                    packaging_cost=Decimal("0"),
                    inbound_logistics_cost=Decimal("0"),
                    additional_cost=Decimal("0"),
                    currency="RUB",
                    effective_from=date(2026, 1, 1),
                )
            )
            await session.flush()
            persist = WbFinancialPersistService(session, user_id)
            costs = await persist.load_cost_snapshots(session, user_id)
            enriched = WbFinancialProcessor.enrich_with_costs(processed, costs)
            await persist.persist(
                report=report,
                file_checksum=checksum,
                storage_uri=report.file_path or "",
                result=enriched,
            )
    return user_id, report_id


async def observe_live_snapshots(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
) -> LiveSnapshotObservation:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            row_count = (
                await session.execute(
                    select(func.count())
                    .select_from(WarehouseStockSnapshot)
                    .where(WarehouseStockSnapshot.user_id == user_id)
                )
            ).scalar_one()
            total_actual = (
                await session.execute(
                    select(func.coalesce(func.sum(WarehouseStockSnapshot.actual_stock), 0)).where(
                        WarehouseStockSnapshot.user_id == user_id
                    )
                )
            ).scalar_one()
            distinct_keys = (
                await session.execute(
                    select(
                        func.count(
                            func.distinct(
                                func.concat(
                                    WarehouseStockSnapshot.snapshot_date,
                                    WarehouseStockSnapshot.sku,
                                    WarehouseStockSnapshot.warehouse_name,
                                )
                            )
                        )
                    ).where(WarehouseStockSnapshot.user_id == user_id)
                )
            ).scalar_one()
    return LiveSnapshotObservation(
        row_count=int(row_count),
        total_actual_stock=int(total_actual),
        distinct_keys=int(distinct_keys),
    )


async def count_staging_rows(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
) -> int:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            return (
                await session.execute(
                    select(func.count())
                    .select_from(WarehouseStockSnapshotStaging)
                    .where(WarehouseStockSnapshotStaging.user_id == user_id)
                )
            ).scalar_one()


async def run_full_rebuild_timed(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
) -> RebuildTiming:
    started = perf_counter()
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            service = FullInventoryRebuildService(session, user_id)
            await service.rebuild()
            row_count = (
                await session.execute(
                    select(func.count())
                    .select_from(WarehouseStockSnapshot)
                    .where(WarehouseStockSnapshot.user_id == user_id)
                )
            ).scalar_one()
    duration_ms = (perf_counter() - started) * 1000
    return RebuildTiming(duration_ms=round(duration_ms, 2), row_count=int(row_count))


async def orchestrate_full_rebuild_pause_before_promote(
    session: AsyncSession,
    user_id: UUID,
    *,
    pause_before_promote: asyncio.Event,
    reader_observed_old: asyncio.Event,
) -> tuple[UUID, list[WarehouseStockSnapshotDraft]]:
    """
    Mirror FullInventoryRebuildService steps using public APIs only.

    Pauses after staging is populated, before promote_staging_to_live (delete + insert).
    """
    await acquire_inventory_rebuild_lock(session, user_id)
    store = InventorySnapshotStore(session, user_id)
    stream = InventoryLedgerStreamingService(session, user_id)
    rebuild_run_id = uuid4()

    await store.clear_staging_run(rebuild_run_id)

    result = await session.execute(
        select(
            func.min(InventoryLedgerEntry.operation_date),
            func.max(InventoryLedgerEntry.operation_date),
        ).where(InventoryLedgerEntry.user_id == user_id)
    )
    min_date, max_date = result.one()
    if min_date is None or max_date is None:
        return rebuild_run_id, []

    costs = await _load_costs(session, user_id)
    ledger_stream = stream.stream_grouped_by_key(rebuild_from=None, carry_forward_keys=set())
    snapshots, _ = await InventorySnapshotComputeService.compute_full_from_stream(
        ledger_stream,
        costs_by_sku=costs,
        rebuild_from=min_date,
        rebuild_to=max_date,
    )
    if snapshots:
        await store.insert_staging_batch(snapshots, rebuild_run_id=rebuild_run_id)
        pause_before_promote.set()
        await reader_observed_old.wait()
        await store.promote_staging_to_live(rebuild_run_id)
        await store.clear_staging_run(rebuild_run_id)
    return rebuild_run_id, snapshots


async def _load_costs(session: AsyncSession, user_id: UUID) -> dict[str, list[SkuCostSnapshot]]:
    result = await session.execute(select(CostHistory).where(CostHistory.user_id == user_id))
    costs: dict[str, list[SkuCostSnapshot]] = {}
    for row in result.scalars().all():
        costs.setdefault(row.internal_sku, []).append(
            SkuCostSnapshot(
                sku=row.internal_sku,
                effective_from=row.effective_from,
                product_cost=row.product_cost,
                packaging_cost=row.packaging_cost,
                inbound_logistics_cost=row.inbound_logistics_cost,
                additional_cost=row.additional_cost,
                currency=row.currency,
            )
        )
    return costs


async def ledger_entry_count(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    *,
    report_id: UUID | None = None,
) -> int:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            stmt = select(func.count()).select_from(InventoryLedgerEntry).where(
                InventoryLedgerEntry.user_id == user_id
            )
            if report_id is not None:
                stmt = stmt.where(InventoryLedgerEntry.report_id == report_id)
            return (await session.execute(stmt)).scalar_one()


async def corrupt_snapshot_actual_stock(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    *,
    snapshot_date: date,
    sku: str,
    warehouse_name: str,
    corrupt_value: int,
) -> int:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            result = await session.execute(
                update(WarehouseStockSnapshot)
                .where(
                    WarehouseStockSnapshot.user_id == user_id,
                    WarehouseStockSnapshot.snapshot_date == snapshot_date,
                    WarehouseStockSnapshot.sku == sku,
                    WarehouseStockSnapshot.warehouse_name == warehouse_name,
                )
                .values(actual_stock=corrupt_value)
            )
            return int(result.rowcount)  # type: ignore[attr-defined, union-attr]

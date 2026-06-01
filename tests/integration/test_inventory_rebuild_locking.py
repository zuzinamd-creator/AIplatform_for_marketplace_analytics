"""Concurrent inventory rebuild locking (requires PostgreSQL + RUN_INTEGRATION_TESTS=true)."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.inventory_rebuild_lock import acquire_inventory_rebuild_lock
from app.core.security_context import TenantSession
from app.domain.inventory.errors import InventoryRebuildBusyError
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry, WarehouseStockSnapshot
from app.models.inventory.enums import InventoryOperationType
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _seed_tenant_with_ledger(session: AsyncSession, user_id) -> None:
    report_id = uuid4()
    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="lock_test.csv",
        file_path="reports/lock_test.csv",
        file_checksum=f"checksum-{uuid4()}",
        status=ReportStatus.PROCESSED,
    )
    session.add(report)
    await session.flush()
    session.add(
        CostHistory(
            user_id=user_id,
            internal_sku="SKU-LOCK",
            cost=Decimal("10"),
            product_cost=Decimal("10"),
            packaging_cost=Decimal("0"),
            inbound_logistics_cost=Decimal("0"),
            additional_cost=Decimal("0"),
            currency="RUB",
            effective_from=date(2026, 1, 1),
        )
    )
    payload = {"source": "test"}
    session.add(
        InventoryLedgerEntry(
            user_id=user_id,
            report_id=report_id,
            operation_date=date(2026, 1, 10),
            sku="SKU-LOCK",
            nm_id=None,
            warehouse_name="WH-1",
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=5,
            cost_per_unit=Decimal("10"),
            sale_price_per_unit=None,
            total_cost_delta=Decimal("50"),
            total_sale_delta=Decimal("0"),
            source_row_id="row-1",
            semantics_version="1.0",
            canonical_payload=payload,
            raw_payload=payload,
        )
    )
    session.add(
        InventoryLedgerEntry(
            user_id=user_id,
            report_id=report_id,
            operation_date=date(2026, 1, 11),
            sku="SKU-LOCK",
            nm_id=None,
            warehouse_name="WH-1",
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-2,
            cost_per_unit=Decimal("10"),
            sale_price_per_unit=Decimal("20"),
            total_cost_delta=Decimal("-20"),
            total_sale_delta=Decimal("40"),
            source_row_id="row-2",
            semantics_version="1.0",
            canonical_payload=payload,
            raw_payload=payload,
        )
    )
    await session.flush()


@pytest.mark.integration
async def test_second_session_fails_fast_on_advisory_lock(db_engine) -> None:
    """Non-blocking lock: contender aborts immediately while holder keeps xact lock."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
    )
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as setup_session:
        async with setup_session.begin():
            setup_session.add(user)
            await setup_session.flush()
        async with TenantSession.transaction(setup_session, user_id):
            await _seed_tenant_with_ledger(setup_session, user_id)

    holder_acquired = asyncio.Event()
    contender_finished = asyncio.Event()

    async def holder() -> None:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                await acquire_inventory_rebuild_lock(session, user_id)
                holder_acquired.set()
                await asyncio.wait_for(contender_finished.wait(), timeout=10.0)

    async def contender() -> None:
        await holder_acquired.wait()
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                with pytest.raises(InventoryRebuildBusyError) as exc_info:
                    await acquire_inventory_rebuild_lock(session, user_id)
                assert exc_info.value.retryable is True
                assert "already running" in str(exc_info.value).lower()
        contender_finished.set()

    await asyncio.gather(holder(), contender())


@pytest.mark.integration
async def test_concurrent_rebuild_only_one_executes_snapshots_consistent(db_engine) -> None:
    """Full rebuild: one session completes; the other gets InventoryRebuildBusyError."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
    )
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as setup_session:
        async with setup_session.begin():
            setup_session.add(user)
            await setup_session.flush()
        async with TenantSession.transaction(setup_session, user_id):
            await _seed_tenant_with_ledger(setup_session, user_id)

    holder_started_rebuild = asyncio.Event()
    contender_attempted = asyncio.Event()

    async def holder_rebuild() -> None:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                await acquire_inventory_rebuild_lock(session, user_id)
                holder_started_rebuild.set()
                await asyncio.wait_for(contender_attempted.wait(), timeout=10.0)
                service = InventorySnapshotRebuildService(session, user_id)
                await service.rebuild(earliest_affected_date=date(2026, 1, 10))

    async def contender_rebuild() -> None:
        await holder_started_rebuild.wait()
        try:
            async with session_factory() as session:
                async with TenantSession.transaction(session, user_id):
                    service = InventorySnapshotRebuildService(session, user_id)
                    with pytest.raises(InventoryRebuildBusyError):
                        await service.rebuild(earliest_affected_date=date(2026, 1, 10))
        finally:
            contender_attempted.set()

    await asyncio.gather(holder_rebuild(), contender_rebuild())

    async with session_factory() as verify_session:
        async with TenantSession.transaction(verify_session, user_id):
            snap_count = (
                await verify_session.execute(
                    select(func.count())
                    .select_from(WarehouseStockSnapshot)
                    .where(WarehouseStockSnapshot.user_id == user_id)
                )
            ).scalar_one()
            duplicate_check = await verify_session.execute(
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
            day11 = (
                await verify_session.execute(
                    select(WarehouseStockSnapshot).where(
                        WarehouseStockSnapshot.user_id == user_id,
                        WarehouseStockSnapshot.snapshot_date == date(2026, 1, 11),
                    )
                )
            ).scalar_one()

    assert snap_count >= 2
    assert duplicate_check.all() == []
    assert day11.opening_stock == 5
    assert day11.expected_closing_stock == 3

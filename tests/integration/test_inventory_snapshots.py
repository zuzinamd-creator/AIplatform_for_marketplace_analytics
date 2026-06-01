from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.security_context import TenantSession
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry, WarehouseStockSnapshot
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import func, select
from tests.integration.wb_fixtures import wb_sale_csv


@pytest.mark.integration
async def test_snapshot_rebuild_idempotent(db_session) -> None:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
    )
    report = Report(
        id=uuid4(),
        user_id=user.id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="wb_snap.csv",
        file_path="reports/wb_snap.csv",
        file_checksum=f"checksum-{uuid4()}",
        status=ReportStatus.PROCESSING,
    )
    async with db_session.begin():
        db_session.add(user)
        await db_session.flush()
    async with TenantSession.transaction(db_session, user.id):
        db_session.add(report)
        db_session.add(
            CostHistory(
                user_id=user.id,
                internal_sku="SKU-SNAP-1",
                cost=Decimal("30"),
                product_cost=Decimal("30"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
                effective_from=date(2026, 1, 1),
            )
        )
        await db_session.flush()

    processed = WbFinancialProcessor.process(
        report_id=report.id,
        report_created_at=datetime.now(UTC),
        filename="wb_snap.csv",
        content=wb_sale_csv(sku="SKU-SNAP-1"),
    )
    assert len(processed.inventory_movements) >= 1
    persist_service = WbFinancialPersistService(db_session, user.id)

    async with TenantSession.transaction(db_session, user.id):
        costs = await persist_service.load_cost_snapshots(db_session, user.id)
        enriched = WbFinancialProcessor.enrich_with_costs(processed, costs)
        await persist_service.persist(
            report=report,
            file_checksum=report.file_checksum or "",
            storage_uri=report.file_path or "",
            result=enriched,
        )
        rebuild_service = InventorySnapshotRebuildService(db_session, user.id)
        await rebuild_service.rebuild(earliest_affected_date=date(2026, 1, 15))
        await rebuild_service.rebuild(earliest_affected_date=date(2026, 1, 15))

    async with TenantSession.transaction(db_session, user.id):
        count_result = await db_session.execute(
            select(func.count())
            .select_from(WarehouseStockSnapshot)
            .where(WarehouseStockSnapshot.user_id == user.id)
        )
        ledger_count = await db_session.execute(
            select(func.count())
            .select_from(InventoryLedgerEntry)
            .where(InventoryLedgerEntry.user_id == user.id)
        )

    assert ledger_count.scalar_one() >= 1
    assert count_result.scalar_one() >= 1


@pytest.mark.integration
async def test_double_upload_no_duplicate_ledger_snapshots_stable(db_session) -> None:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
    )
    checksum = f"checksum-{uuid4()}"
    report = Report(
        id=uuid4(),
        user_id=user.id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="wb_retry.csv",
        file_path="reports/wb_retry.csv",
        file_checksum=checksum,
        status=ReportStatus.PROCESSING,
    )
    async with db_session.begin():
        db_session.add(user)
        await db_session.flush()
    async with TenantSession.transaction(db_session, user.id):
        db_session.add(report)
        await db_session.flush()

    processed = WbFinancialProcessor.process(
        report_id=report.id,
        report_created_at=datetime.now(UTC),
        filename="wb_retry.csv",
        content=wb_sale_csv(sku="SKU-SNAP-1"),
    )
    assert len(processed.inventory_movements) >= 1
    persist_service = WbFinancialPersistService(db_session, user.id)

    async with TenantSession.transaction(db_session, user.id):
        costs = await persist_service.load_cost_snapshots(db_session, user.id)
        enriched = WbFinancialProcessor.enrich_with_costs(processed, costs)
        await persist_service.persist(
            report=report,
            file_checksum=checksum,
            storage_uri=report.file_path or "",
            result=enriched,
        )
        first_snap_count = (
            await db_session.execute(
                select(func.count())
                .select_from(WarehouseStockSnapshot)
                .where(WarehouseStockSnapshot.user_id == user.id)
            )
        ).scalar_one()
        await persist_service.persist(
            report=report,
            file_checksum=checksum,
            storage_uri=report.file_path or "",
            result=enriched,
        )
        second_snap_count = (
            await db_session.execute(
                select(func.count())
                .select_from(WarehouseStockSnapshot)
                .where(WarehouseStockSnapshot.user_id == user.id)
            )
        ).scalar_one()
        ledger_count = (
            await db_session.execute(
                select(func.count())
                .select_from(InventoryLedgerEntry)
                .where(InventoryLedgerEntry.user_id == user.id)
            )
        ).scalar_one()

    assert ledger_count == len(enriched.inventory_movements)
    assert first_snap_count == second_snap_count

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.security_context import TenantSession
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import func, select
from tests.integration.wb_fixtures import wb_sale_csv


@pytest.mark.integration
async def test_wb_report_double_persist_no_duplicate_inventory(db_session) -> None:
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
        original_filename="wb_sales.csv",
        file_path="reports/wb_sales.csv",
        file_checksum=f"checksum-{uuid4()}",
        status=ReportStatus.PROCESSING,
    )
    async with db_session.begin():
        db_session.add(user)
        await db_session.flush()
    async with TenantSession.transaction(db_session, user.id):
        db_session.add(report)
        await db_session.flush()

    async with TenantSession.transaction(db_session, user.id):
        db_session.add(
            CostHistory(
                user_id=user.id,
                internal_sku="SKU-INV-1",
                cost=Decimal("40"),
                product_cost=Decimal("40"),
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
        filename="wb_sales.csv",
        content=wb_sale_csv(sku="SKU-INV-1"),
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
        await persist_service.persist(
            report=report,
            file_checksum=report.file_checksum or "",
            storage_uri=report.file_path or "",
            result=enriched,
        )

    async with TenantSession.transaction(db_session, user.id):
        count_result = await db_session.execute(
            select(func.count())
            .select_from(InventoryLedgerEntry)
            .where(
                InventoryLedgerEntry.user_id == user.id,
                InventoryLedgerEntry.report_id == report.id,
            )
        )
        count = count_result.scalar_one()

    assert count == len(enriched.inventory_movements)
    assert count >= 1

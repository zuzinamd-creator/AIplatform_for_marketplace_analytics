"""
End-to-end integration: WB weekly XLSX -> processor -> persist -> PostgreSQL.

Requires:
  RUN_INTEGRATION_TESTS=true
  TEST_DATABASE_URL (default: postgresql+asyncpg://...@localhost:5434/marketplace_test)
  alembic upgrade head on the test database
  tests/*.xlsx — trimmed 'Еженедельный детализированный отчет WB.xlsx'
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core.security_context import TenantSession
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.models.finance import (
    FinancialLedgerEntry,
    NormalizedReportRow,
    RawReport,
    ReportReconciliation,
)
from app.models.inventory import InventoryLedgerEntry
from app.models.report import Report
from app.models.user import User
from sqlalchemy import func, select


@pytest.mark.integration
async def test_report_persisted_from_weekly_xlsx(
    db_session,
    integration_user: User,
    make_wb_report,
    wb_weekly_report_bytes: bytes,
    wb_weekly_report_file,
    wb_weekly_report_checksum: str,
) -> None:
    """Report row + financial layers are written and readable after WB XLSX ingest."""
    report = make_wb_report()
    created_at = datetime.now(UTC)

    processed = WbFinancialProcessor.process(
        report_id=report.id,
        report_created_at=created_at,
        filename=wb_weekly_report_file.name,
        content=wb_weekly_report_bytes,
    )
    assert processed.row_count > 0
    assert len(processed.normalized_rows) > 0
    assert len(processed.ledger_entries) > 0

    async with TenantSession.transaction(db_session, integration_user.id):
        db_session.add(report)
        await db_session.flush()

        persist_service = WbFinancialPersistService(db_session, integration_user.id)
        await persist_service.persist(
            report=report,
            file_checksum=wb_weekly_report_checksum,
            storage_uri=report.file_path or "",
            result=processed,
        )

    async with TenantSession.transaction(db_session, integration_user.id):
        loaded = await db_session.get(Report, report.id)
        assert loaded is not None
        assert loaded.user_id == integration_user.id
        assert loaded.marketplace.value == "wildberries"
        assert loaded.original_filename == wb_weekly_report_file.name
        assert loaded.file_checksum == wb_weekly_report_checksum

        raw_count = (
            await db_session.execute(
                select(func.count()).select_from(RawReport).where(RawReport.report_id == report.id)
            )
        ).scalar_one()
        normalized_count = (
            await db_session.execute(
                select(func.count())
                .select_from(NormalizedReportRow)
                .where(NormalizedReportRow.report_id == report.id)
            )
        ).scalar_one()
        ledger_count = (
            await db_session.execute(
                select(func.count())
                .select_from(FinancialLedgerEntry)
                .where(FinancialLedgerEntry.report_id == report.id)
            )
        ).scalar_one()
        inventory_count = (
            await db_session.execute(
                select(func.count())
                .select_from(InventoryLedgerEntry)
                .where(InventoryLedgerEntry.report_id == report.id)
            )
        ).scalar_one()
        reconciliation_count = (
            await db_session.execute(
                select(func.count())
                .select_from(ReportReconciliation)
                .where(ReportReconciliation.report_id == report.id)
            )
        ).scalar_one()

    expected_financial_ledger = len({entry.source_row_id for entry in processed.ledger_entries})

    assert raw_count == 1
    assert normalized_count == len(processed.normalized_rows)
    assert ledger_count == expected_financial_ledger
    assert inventory_count == len(processed.inventory_movements)
    assert reconciliation_count == 1

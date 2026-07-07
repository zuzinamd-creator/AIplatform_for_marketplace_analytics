"""Unit tests for ETL period column persistence."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.models.report import Marketplace, Report, ReportType
from app.services.report_service import ReportService


@pytest.mark.asyncio
async def test_persist_business_result_sets_period_columns() -> None:
    user_id = uuid4()
    report = Report(
        id=uuid4(),
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.FINANCE,
        original_filename="wb.xlsx",
        file_path="/tmp/wb.xlsx",
        file_checksum="abc123",
    )
    db = AsyncMock()
    service = ReportService(db, MagicMock(id=user_id))
    service.user = MagicMock(id=user_id)

    tx_mock = AsyncMock()
    tx_mock.__aenter__ = AsyncMock(return_value=None)
    tx_mock.__aexit__ = AsyncMock(return_value=None)

    with patch.object(service, "_rls_transaction", return_value=tx_mock):
        await service.persist_business_result(
            report,
            raw_data={"period_start": "2026-05-01", "period_end": "2026-05-07"},
            row_count=10,
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 7),
        )

    assert report.period_start == date(2026, 5, 1)
    assert report.period_end == date(2026, 5, 7)
    assert report.row_count == 10

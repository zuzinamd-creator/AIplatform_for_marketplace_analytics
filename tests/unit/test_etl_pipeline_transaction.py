"""Tests for ETL pipeline transaction safety during worker persist."""

from __future__ import annotations

import builtins
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.etl.pipeline import ETLPipeline
from app.etl.types import ETLResult
from app.etl.wb.types import WbFinancialProcessResult
from app.models.report import Marketplace, Report, ReportType


@pytest.mark.asyncio
async def test_persist_result_skips_commit_when_in_transaction(monkeypatch) -> None:
    db = AsyncMock()
    db.commit = AsyncMock()
    user_id = uuid4()
    report = Report(
        id=uuid4(),
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.FINANCE,
        original_filename="test.xlsx",
        file_path="/tmp/test.xlsx",
        file_checksum="abc",
    )
    wb_mock = MagicMock()
    wb_mock.raw_snapshot = {"rows": []}
    wb_mock.row_count = 0
    wb_mock.analytics_payload = {"report_id": str(report.id)}
    wb_mock.normalized_rows = []
    wb_mock.etl_anomalies = ()

    etl_result = ETLResult(
        raw_data={"rows": []},
        row_count=0,
        analytics_payload={"report_id": str(report.id)},
        wb_financial=wb_mock,
    )
    report_service = MagicMock()
    report_service.persist_business_result = AsyncMock(return_value=report)

    real_isinstance = builtins.isinstance

    def _isinstance(obj, cls):  # noqa: ANN001
        if cls is WbFinancialProcessResult and obj is wb_mock:
            return True
        return real_isinstance(obj, cls)

    monkeypatch.setattr(builtins, "isinstance", _isinstance)

    pipeline = ETLPipeline(db, user_id)
    with patch("app.etl.pipeline.WbFinancialPersistService") as persist_cls:
        persist_instance = persist_cls.return_value
        persist_instance.load_cost_snapshots = AsyncMock(return_value={})
        persist_instance.persist = AsyncMock(return_value={})
        with patch("app.etl.pipeline.WbFinancialProcessor.enrich_with_costs") as enrich:
            enrich.return_value = wb_mock
            with patch("app.etl.pipeline.extend_analytics_payload") as extend:
                extend.return_value = wb_mock.analytics_payload
                with patch.object(pipeline, "_prepare_ai_context_idempotent", AsyncMock()):
                    with patch.object(pipeline, "_persist_etl_anomalies_best_effort", AsyncMock()):
                        with patch(
                            "app.etl.pipeline.fetch_sale_period_bounds_for_reports",
                            AsyncMock(return_value={}),
                        ):
                            await pipeline.persist_result(
                                report,
                                etl_result,
                                report_service,
                                in_transaction=True,
                            )

    db.commit.assert_not_called()

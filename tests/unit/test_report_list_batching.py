import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.job import EtlJob, JobStatus
from app.models.report import Marketplace, Report, ReportType
from app.services.report_service import ReportService


def _report(report_id: uuid.UUID, user_id: uuid.UUID) -> Report:
    return Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.FINANCE,
        original_filename="report.xlsx",
        file_path="uploads/x",
        file_checksum=f"checksum-{report_id}",
    )


@pytest.mark.asyncio
async def test_list_reports_uses_single_rls_transaction() -> None:
    user_id = uuid.uuid4()
    report_ids = [uuid.uuid4(), uuid.uuid4()]
    reports = [_report(rid, user_id) for rid in report_ids]
    jobs = {
        report_ids[0]: EtlJob(
            id=uuid.uuid4(),
            user_id=user_id,
            report_id=report_ids[0],
            status=JobStatus.COMPLETED,
            idempotency_key="a",
            created_at=datetime.now(UTC),
        )
    }

    db = AsyncMock()
    service = ReportService(db, MagicMock(id=user_id))
    service.user = MagicMock(id=user_id)

    tx_mock = AsyncMock()
    tx_mock.__aenter__ = AsyncMock(return_value=None)
    tx_mock.__aexit__ = AsyncMock(return_value=None)

    with patch.object(service, "_rls_transaction", return_value=tx_mock) as rls_mock:
        with patch.object(service, "_latest_jobs_for_reports", AsyncMock(return_value=jobs)) as jobs_mock:
            with patch.object(
                service,
                "_period_bounds_for_report_ids",
                AsyncMock(return_value={report_ids[0]: (None, None)}),
            ) as bounds_mock:
                db.execute = AsyncMock(
                    return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=reports))))
                )
                with patch(
                    "app.services.report_service.report_to_response",
                    side_effect=lambda report, job, **kw: MagicMock(id=report.id, job=job),
                ) as map_mock:
                    rows = await service.list_reports()

    rls_mock.assert_called_once()
    jobs_mock.assert_awaited_once_with(report_ids)
    bounds_mock.assert_awaited_once_with(report_ids)
    assert map_mock.call_count == 2
    assert len(rows) == 2

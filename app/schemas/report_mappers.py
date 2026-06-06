from datetime import date

from sqlalchemy import inspect

from app.models.job import EtlJob
from app.models.report import Report
from app.schemas.report import ReportResponse
from app.schemas.report_projection import (
    derive_error_message,
    derive_processed_at,
    derive_report_status,
)


def _period_from_raw_data(raw_data: dict | None) -> tuple[date | None, date | None]:
    if not raw_data:
        return None, None
    start = raw_data.get("period_start")
    end = raw_data.get("period_end")
    if isinstance(start, str):
        start = date.fromisoformat(start)
    if isinstance(end, str):
        end = date.fromisoformat(end)
    if not isinstance(start, date):
        start = None
    if not isinstance(end, date):
        end = None
    return start, end


def report_to_response(
    report: Report,
    job: EtlJob | None = None,
    *,
    period_start: date | None = None,
    period_end: date | None = None,
) -> ReportResponse:
    """Stable API mapping; processing state projected from latest etl_job."""
    state = inspect(report)
    if "raw_data" in state.unloaded:
        raw_start, raw_end = None, None
    else:
        raw_start, raw_end = _period_from_raw_data(report.raw_data)
    return ReportResponse(
        id=report.id,
        user_id=report.user_id,
        marketplace=report.marketplace,
        report_type=report.report_type,
        original_filename=report.original_filename,
        file_path=report.file_path,
        status=derive_report_status(job),
        row_count=report.row_count,
        error_message=derive_error_message(report, job),
        attempt_count=job.attempt_count if job else 0,
        max_attempts=job.max_attempts if job else 3,
        idempotency_key=report.file_checksum or (job.idempotency_key if job else None),
        claimed_at=job.claimed_at if job else None,
        processed_at=derive_processed_at(report, job),
        period_start=period_start or raw_start,
        period_end=period_end or raw_end,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )

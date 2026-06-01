from app.models.job import EtlJob
from app.models.report import Report
from app.schemas.report import ReportResponse
from app.schemas.report_projection import (
    derive_error_message,
    derive_processed_at,
    derive_report_status,
)


def report_to_response(report: Report, job: EtlJob | None = None) -> ReportResponse:
    """Stable API mapping; processing state projected from latest etl_job."""
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
        created_at=report.created_at,
        updated_at=report.updated_at,
    )

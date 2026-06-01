from datetime import UTC, datetime
from uuid import uuid4

from app.models.job import EtlJob, JobStatus
from app.models.report import ReportStatus
from app.schemas.report_projection import derive_report_status


def _job(status: JobStatus) -> EtlJob:
    return EtlJob(
        id=uuid4(),
        user_id=uuid4(),
        report_id=uuid4(),
        job_type="etl_process_report",
        status=status,
        attempt_count=1,
        max_attempts=3,
        visibility_timeout_seconds=1800,
        idempotency_key="abc",
        marketplace="wildberries",
        report_type="sales",
        original_filename="f.csv",
        report_created_at=datetime.now(UTC),
    )


def test_derive_report_status_pending() -> None:
    assert derive_report_status(_job(JobStatus.PENDING)) == ReportStatus.PENDING


def test_derive_report_status_processing() -> None:
    assert derive_report_status(_job(JobStatus.PROCESSING)) == ReportStatus.PROCESSING


def test_derive_report_status_completed() -> None:
    assert derive_report_status(_job(JobStatus.COMPLETED)) == ReportStatus.PROCESSED


def test_derive_report_status_dead_letter_maps_failed() -> None:
    assert derive_report_status(_job(JobStatus.DEAD_LETTER)) == ReportStatus.FAILED


def test_derive_report_status_without_job() -> None:
    assert derive_report_status(None) == ReportStatus.PENDING

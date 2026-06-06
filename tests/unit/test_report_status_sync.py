from app.models.job import JobStatus
from app.models.report import ReportStatus
from app.schemas.report_projection import report_status_from_job_status


def test_report_status_from_job_status_mapping() -> None:
    assert report_status_from_job_status(JobStatus.COMPLETED) == ReportStatus.PROCESSED
    assert report_status_from_job_status(JobStatus.PROCESSING) == ReportStatus.PROCESSING
    assert report_status_from_job_status(JobStatus.FAILED) == ReportStatus.FAILED
    assert report_status_from_job_status(JobStatus.DEAD_LETTER) == ReportStatus.FAILED

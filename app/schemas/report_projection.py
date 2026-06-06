"""
API projection layer: processing lifecycle is derived from etl_jobs only.
"""

from app.models.job import EtlJob, JobStatus
from app.models.report import Report, ReportStatus


_JOB_TO_REPORT_STATUS: dict[JobStatus, ReportStatus] = {
    JobStatus.PENDING: ReportStatus.PENDING,
    JobStatus.PROCESSING: ReportStatus.PROCESSING,
    JobStatus.COMPLETED: ReportStatus.PROCESSED,
    JobStatus.FAILED: ReportStatus.FAILED,
    JobStatus.DEAD_LETTER: ReportStatus.FAILED,
}


def report_status_from_job_status(job_status: JobStatus) -> ReportStatus:
    return _JOB_TO_REPORT_STATUS.get(job_status, ReportStatus.PENDING)


def derive_report_status(job: EtlJob | None) -> ReportStatus:
    """Map latest job state to stable API ReportStatus."""
    if job is None:
        return ReportStatus.PENDING
    return report_status_from_job_status(job.status)


def derive_error_message(report: Report, job: EtlJob | None) -> str | None:
    if job and job.last_error:
        return job.last_error
    return report.error_message


def derive_processed_at(report: Report, job: EtlJob | None):
    if job and job.status == JobStatus.COMPLETED:
        return job.completed_at or report.processed_at
    return report.processed_at

"""
API projection layer: processing lifecycle is derived from etl_jobs only.
"""

from app.models.job import EtlJob, JobStatus
from app.models.report import Report, ReportStatus


def derive_report_status(job: EtlJob | None) -> ReportStatus:
    """Map latest job state to stable API ReportStatus."""
    if job is None:
        return ReportStatus.PENDING

    mapping: dict[JobStatus, ReportStatus] = {
        JobStatus.PENDING: ReportStatus.PENDING,
        JobStatus.PROCESSING: ReportStatus.PROCESSING,
        JobStatus.COMPLETED: ReportStatus.PROCESSED,
        JobStatus.FAILED: ReportStatus.FAILED,
        JobStatus.DEAD_LETTER: ReportStatus.FAILED,
    }
    return mapping.get(job.status, ReportStatus.PENDING)


def derive_error_message(report: Report, job: EtlJob | None) -> str | None:
    if job and job.last_error:
        return job.last_error
    return report.error_message


def derive_processed_at(report: Report, job: EtlJob | None):
    if job and job.status == JobStatus.COMPLETED:
        return job.completed_at or report.processed_at
    return report.processed_at

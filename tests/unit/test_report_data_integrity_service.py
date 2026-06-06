"""Unit tests for report ↔ job integrity projection."""

from app.services.report_data_integrity_service import ReportDataIntegrityStatus


def test_integrity_healthy_when_no_gaps() -> None:
    status = ReportDataIntegrityStatus(
        total_reports=3,
        total_cost_rows=10,
        reports_without_job=0,
        reports_without_file_path=0,
        orphan_etl_jobs=0,
        sample_report_ids_without_job=[],
    )
    assert status.healthy is True


def test_integrity_unhealthy_when_reports_missing_jobs() -> None:
    status = ReportDataIntegrityStatus(
        total_reports=2,
        total_cost_rows=0,
        reports_without_job=1,
        reports_without_file_path=0,
        orphan_etl_jobs=0,
        sample_report_ids_without_job=[],
    )
    assert status.healthy is False

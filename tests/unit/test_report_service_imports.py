"""Regression: report list must not fail on missing SQLAlchemy imports."""

from app.services import report_service


def test_report_service_imports_sqlalchemy_func() -> None:
    assert hasattr(report_service, "func")

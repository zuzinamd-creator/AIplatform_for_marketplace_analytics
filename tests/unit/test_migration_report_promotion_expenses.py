"""Migration smoke test for promotion_expenses column."""

from pathlib import Path


def test_migration_report_promotion_expenses_exists() -> None:
    path = Path("alembic/versions/0033_report_promotion_expenses.py")
    text = path.read_text(encoding="utf-8")
    assert "promotion_expenses" in text
    assert "ck_reports_promotion_expenses_nonneg" in text
    assert "0032_lockdown_backend_tables" in text

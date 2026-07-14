"""Migration smoke test for jam_subscription_expenses column."""

from pathlib import Path


def test_migration_report_jam_subscription_expenses_exists() -> None:
    path = Path("alembic/versions/0036_report_jam_subscription_expenses.py")
    text = path.read_text(encoding="utf-8")
    assert "jam_subscription_expenses" in text
    assert "ck_reports_jam_subscription_expenses_nonneg" in text
    assert 'down_revision: str | Sequence[str] | None = "0035_registration_invites"' in text

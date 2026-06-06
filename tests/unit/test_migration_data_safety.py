"""Alembic migrations must not TRUNCATE or DELETE from tenant data tables."""

from pathlib import Path

USER_DATA_TABLES = {
    "reports",
    "etl_jobs",
    "cost_history",
    "financial_ledger_entries",
    "raw_reports",
    "normalized_report_rows",
}

FORBIDDEN_PATTERNS = (
    "TRUNCATE TABLE",
    "DELETE FROM",
)


def test_alembic_migrations_do_not_wipe_user_data() -> None:
    versions_dir = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    violations: list[str] = []
    for path in sorted(versions_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        for table in USER_DATA_TABLES:
            for pattern in FORBIDDEN_PATTERNS:
                needle = f"{pattern.lower()} {table}"
                if needle in text:
                    violations.append(f"{path.name}: {pattern} {table}")
    assert not violations, "Unsafe data-destructive migrations found:\n" + "\n".join(violations)

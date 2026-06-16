"""Unit tests for migration 0031 report period columns."""

from pathlib import Path


def test_migration_0031_adds_period_columns_and_backfill() -> None:
    path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0031_report_period_columns.py"
    text = path.read_text(encoding="utf-8")
    assert 'sa.Column("period_start", sa.Date(), nullable=True)' in text
    assert 'sa.Column("period_end", sa.Date(), nullable=True)' in text
    assert "NULLIF(raw_data->>'period_start', '')" in text
    assert "NULLIF(raw_data->>'period_end', '')" in text
    assert "ck_reports_period_range" in text
    assert "period_end >= period_start" in text


def test_migration_0031_downgrade_drops_columns() -> None:
    path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0031_report_period_columns.py"
    text = path.read_text(encoding="utf-8")
    assert "drop_column" in text
    assert '"period_start"' in text
    assert '"period_end"' in text

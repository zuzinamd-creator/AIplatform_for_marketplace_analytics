"""Migration 0032 backend table lockdown."""

from pathlib import Path


def test_migration_0032_revokes_anon_and_adds_backend_policy() -> None:
    path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0032_lockdown_backend_tables.py"
    text = path.read_text(encoding="utf-8")
    assert "REVOKE ALL ON TABLE public.{table_name} FROM anon, authenticated" in text
    assert "ENABLE ROW LEVEL SECURITY" in text
    assert "_backend_only" in text
    assert "TO marketplace_app" in text
    for table in (
        "users",
        "password_reset_tokens",
        "alembic_version",
        "semantics_change_log",
        "semantics_lifecycle_versions",
    ):
        assert f'"{table}"' in text

"""Lock down backend-only public tables from Supabase anon/authenticated.

Revision ID: 0032_lockdown_backend_tables
Revises: 0031_report_period_columns
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032_lockdown_backend_tables"
down_revision: str | Sequence[str] | None = "0031_report_period_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# FastAPI uses marketplace_app; Supabase PostgREST uses anon/authenticated.
BACKEND_ONLY_TABLES: tuple[str, ...] = (
    "users",
    "password_reset_tokens",
    "alembic_version",
    "semantics_change_log",
    "semantics_lifecycle_versions",
)


def _lockdown_table(table_name: str) -> None:
    op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table_name} FROM anon, authenticated"))
    op.execute(sa.text(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_backend_only ON public.{table_name}"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {table_name}_backend_only
            ON public.{table_name}
            FOR ALL
            TO marketplace_app
            USING (true)
            WITH CHECK (true)
            """
        )
    )


def upgrade() -> None:
    for table_name in BACKEND_ONLY_TABLES:
        _lockdown_table(table_name)


def downgrade() -> None:
    for table_name in BACKEND_ONLY_TABLES:
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_backend_only ON public.{table_name}"))
        op.execute(sa.text(f"ALTER TABLE public.{table_name} NO FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE public.{table_name} DISABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{table_name} TO anon, authenticated"
            )
        )

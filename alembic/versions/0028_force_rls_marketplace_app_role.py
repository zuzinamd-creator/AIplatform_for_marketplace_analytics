"""Force RLS on tenant tables and provision marketplace_app DB role.

Revision ID: 0028_force_rls_marketplace_app
Revises: 0027_auth_audit_events
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_force_rls_marketplace_app"
down_revision: str | Sequence[str] | None = "0027_auth_audit_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# User-requested core tenant surfaces + all tables that already have RLS policies.
FORCE_RLS_TABLES: tuple[str, ...] = (
    "reports",
    "cost_history",
    "financial_ledger_entries",
    "daily_aggregates",
    "sku_daily_metrics",
    "products",
    "metrics",
    "sku_mapping",
    "ai_insights",
    "raw_reports",
    "normalized_report_rows",
    "report_reconciliations",
    "inventory_ledger_entries",
    "warehouse_stock_snapshots",
    "warehouse_stock_snapshots_staging",
    "inventory_integrity_anomalies",
    "snapshot_consistency_checks",
    "snapshot_rebuild_requirements",
    "etl_anomalies",
    "etl_jobs",
    "ai_execution_runs",
    "ai_session_turns",
    "ai_recommendations",
    "ai_recommendation_feedback",
    "ai_strategic_memory",
    "auth_audit_events",
    "operator_audit_events",
    "runtime_autonomy_events",
    "runtime_autonomous_actions",
    "runtime_process_heartbeats",
    "runtime_process_leases",
    "runtime_schedule_policies",
    "seller_workflow_events",
    "sku_unit_economics_daily",
    "tenant_containment_states",
)


def _app_password() -> str:
    password = os.environ.get("MARKETPLACE_APP_DB_PASSWORD", "").strip()
    if not password:
        raise RuntimeError(
            "Set MARKETPLACE_APP_DB_PASSWORD before running this migration "
            "(see scripts/setup_marketplace_app_db.sh)."
        )
    return password.replace("'", "''")


def upgrade() -> None:
    password = _app_password()

    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'marketplace_app') THEN
                    CREATE ROLE marketplace_app LOGIN PASSWORD '{password}';
                ELSE
                    ALTER ROLE marketplace_app WITH LOGIN PASSWORD '{password}';
                END IF;
            END
            $$;
            """
        )
    )

    op.execute(sa.text("GRANT CONNECT ON DATABASE postgres TO marketplace_app"))
    op.execute(sa.text("GRANT USAGE ON SCHEMA public TO marketplace_app"))
    op.execute(
        sa.text(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO marketplace_app"
        )
    )
    op.execute(sa.text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO marketplace_app"))
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO marketplace_app"
        )
    )
    op.execute(
        sa.text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO marketplace_app"
        )
    )

    for table_name in FORCE_RLS_TABLES:
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF to_regclass('public.{table_name}') IS NOT NULL THEN
                        EXECUTE 'ALTER TABLE public.{table_name} FORCE ROW LEVEL SECURITY';
                    END IF;
                END
                $$;
                """
            )
        )


def downgrade() -> None:
    for table_name in FORCE_RLS_TABLES:
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF to_regclass('public.{table_name}') IS NOT NULL THEN
                        EXECUTE 'ALTER TABLE public.{table_name} NO FORCE ROW LEVEL SECURITY';
                    END IF;
                END
                $$;
                """
            )
        )
    op.execute(sa.text("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM marketplace_app"))
    op.execute(sa.text("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM marketplace_app"))
    op.execute(sa.text("REVOKE USAGE ON SCHEMA public FROM marketplace_app"))
    op.execute(sa.text("REVOKE CONNECT ON DATABASE postgres FROM marketplace_app"))
    op.execute(sa.text("DROP ROLE IF EXISTS marketplace_app"))

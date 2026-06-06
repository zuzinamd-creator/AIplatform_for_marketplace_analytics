"""Fix etl_jobs RLS: safe tenant cast when queue_role is active.

Revision ID: 0030_etl_queue_rls_fix
Revises: 0029_tenant_aggregate_uniques
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_etl_queue_rls_fix"
down_revision: str | Sequence[str] | None = "0029_tenant_aggregate_uniques"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Avoid evaluating ::uuid on empty app.current_user_id (breaks worker claim/recover).
_ETL_JOBS_POLICY = """
(
    CASE
        WHEN coalesce(current_setting('app.queue_role', true), '') = 'true' THEN true
        WHEN coalesce(current_setting('app.bypass_rls', true), '') = 'true' THEN true
        ELSE user_id = nullif(current_setting('app.current_user_id', true), '')::uuid
    END
)
"""


def upgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS etl_jobs_tenant_isolation ON etl_jobs"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY etl_jobs_tenant_isolation
            ON etl_jobs
            FOR ALL
            USING {_ETL_JOBS_POLICY}
            WITH CHECK {_ETL_JOBS_POLICY}
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS etl_jobs_tenant_isolation ON etl_jobs"))
    op.execute(
        sa.text(
            """
            CREATE POLICY etl_jobs_tenant_isolation
            ON etl_jobs
            FOR ALL
            USING (
                user_id = current_setting('app.current_user_id', true)::uuid
                OR current_setting('app.queue_role', true)::boolean = true
                OR current_setting('app.bypass_rls', true)::boolean = true
            )
            WITH CHECK (
                user_id = current_setting('app.current_user_id', true)::uuid
                OR current_setting('app.queue_role', true)::boolean = true
                OR current_setting('app.bypass_rls', true)::boolean = true
            )
            """
        )
    )

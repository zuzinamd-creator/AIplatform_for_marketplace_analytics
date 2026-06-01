"""queue isolation: etl_jobs snapshots and queue_role RLS

Revision ID: 0003_queue_isolation
Revises: 0002_production_hardening
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_queue_isolation"
down_revision: str | Sequence[str] | None = "0002_production_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("etl_jobs", sa.Column("file_path", sa.String(length=1024), nullable=True))
    op.add_column("etl_jobs", sa.Column("marketplace", sa.String(length=32), nullable=True))
    op.add_column("etl_jobs", sa.Column("report_type", sa.String(length=32), nullable=True))
    op.add_column("etl_jobs", sa.Column("original_filename", sa.String(length=512), nullable=True))
    op.add_column("etl_jobs", sa.Column("report_created_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE etl_jobs j
            SET
                file_path = r.file_path,
                marketplace = r.marketplace::text,
                report_type = r.report_type::text,
                original_filename = r.original_filename,
                report_created_at = r.created_at
            FROM reports r
            WHERE r.id = j.report_id
            """
        )
    )

    op.alter_column("etl_jobs", "marketplace", nullable=False, server_default="wildberries")
    op.alter_column("etl_jobs", "report_type", nullable=False, server_default="sales")
    op.alter_column("etl_jobs", "original_filename", nullable=False, server_default="report.csv")
    op.alter_column("etl_jobs", "report_created_at", nullable=False)

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

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'etl_queue_broker') THEN
                CREATE ROLE etl_queue_broker NOLOGIN;
              END IF;
            END
            $$
            """
        )
    )
    op.execute(sa.text("GRANT SELECT, UPDATE ON etl_jobs TO etl_queue_broker"))


def downgrade() -> None:
    op.execute(sa.text("REVOKE SELECT, UPDATE ON etl_jobs FROM etl_queue_broker"))
    op.execute(sa.text("DROP POLICY IF EXISTS etl_jobs_tenant_isolation ON etl_jobs"))
    op.execute(
        sa.text(
            """
            CREATE POLICY etl_jobs_tenant_isolation
            ON etl_jobs
            FOR ALL
            USING (
                user_id = current_setting('app.current_user_id')::uuid
                OR current_setting('app.bypass_rls', true)::boolean = true
            )
            WITH CHECK (
                user_id = current_setting('app.current_user_id')::uuid
                OR current_setting('app.bypass_rls', true)::boolean = true
            )
            """
        )
    )
    op.drop_column("etl_jobs", "report_created_at")
    op.drop_column("etl_jobs", "original_filename")
    op.drop_column("etl_jobs", "report_type")
    op.drop_column("etl_jobs", "marketplace")
    op.drop_column("etl_jobs", "file_path")

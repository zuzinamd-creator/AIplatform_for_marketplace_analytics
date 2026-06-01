"""production hardening: etl_jobs table and report cleanup

Revision ID: 0002_production_hardening
Revises: 0001_initial
Create Date: 2026-05-25 22:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

revision: str = "0002_production_hardening"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

job_status_enum = postgresql.ENUM(
    "pending",
    "processing",
    "completed",
    "failed",
    name="job_status_enum",
    create_type=False,
)


def upgrade() -> None:
    ensure_pg_enum("job_status_enum", ("pending", "processing", "completed", "failed"))

    op.create_table(
        "etl_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", job_status_enum, nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("visibility_timeout_seconds", sa.Integer(), nullable=False, server_default="1800"),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_etl_job_tenant_idempotency"),
    )
    op.create_index(op.f("ix_etl_jobs_user_id"), "etl_jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_etl_jobs_report_id"), "etl_jobs", ["report_id"], unique=False)
    op.create_index(op.f("ix_etl_jobs_status"), "etl_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_etl_jobs_idempotency_key"), "etl_jobs", ["idempotency_key"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO etl_jobs (
                id, user_id, report_id, job_type, status, attempt_count, max_attempts,
                visibility_timeout_seconds, claimed_at, completed_at, idempotency_key, last_error,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                r.user_id,
                r.id,
                'etl_process_report',
                CASE
                    WHEN r.status::text = 'processed' THEN 'completed'
                    WHEN r.status::text = 'failed' THEN 'failed'
                    WHEN r.status::text = 'processing' THEN 'processing'
                    ELSE 'pending'
                END::job_status_enum,
                COALESCE(r.attempt_count, 0),
                COALESCE(r.max_attempts, 3),
                1800,
                r.claimed_at,
                r.processed_at,
                COALESCE(r.idempotency_key, r.id::text),
                r.error_message,
                r.created_at,
                r.updated_at
            FROM reports r
            """
        )
    )

    op.add_column("reports", sa.Column("file_checksum", sa.String(length=64), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE reports
            SET file_checksum = idempotency_key
            WHERE idempotency_key IS NOT NULL
              AND length(idempotency_key) = 64
            """
        )
    )

    op.drop_index(op.f("ix_reports_idempotency_key"), table_name="reports")
    op.drop_column("reports", "attempt_count")
    op.drop_column("reports", "max_attempts")
    op.drop_column("reports", "idempotency_key")
    op.drop_column("reports", "claimed_at")
    op.create_index(op.f("ix_reports_file_checksum"), "reports", ["file_checksum"], unique=False)
    op.create_unique_constraint("uq_report_tenant_checksum", "reports", ["user_id", "file_checksum"])

    op.execute(sa.text("ALTER TABLE etl_jobs ENABLE ROW LEVEL SECURITY"))
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


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS etl_jobs_tenant_isolation ON etl_jobs"))
    op.execute(sa.text("ALTER TABLE etl_jobs DISABLE ROW LEVEL SECURITY"))

    op.drop_constraint("uq_report_tenant_checksum", "reports", type_="unique")
    op.drop_index(op.f("ix_reports_file_checksum"), table_name="reports")

    op.add_column("reports", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("reports", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.add_column("reports", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("reports", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))

    op.execute(
        sa.text(
            """
            UPDATE reports r
            SET
                attempt_count = j.attempt_count,
                max_attempts = j.max_attempts,
                claimed_at = j.claimed_at,
                idempotency_key = j.idempotency_key
            FROM etl_jobs j
            WHERE j.report_id = r.id
            """
        )
    )

    op.drop_column("reports", "file_checksum")
    op.create_index(op.f("ix_reports_idempotency_key"), "reports", ["idempotency_key"], unique=True)

    op.drop_index(op.f("ix_etl_jobs_idempotency_key"), table_name="etl_jobs")
    op.drop_index(op.f("ix_etl_jobs_status"), table_name="etl_jobs")
    op.drop_index(op.f("ix_etl_jobs_report_id"), table_name="etl_jobs")
    op.drop_index(op.f("ix_etl_jobs_user_id"), table_name="etl_jobs")
    op.drop_table("etl_jobs")
    job_status_enum.drop(op.get_bind(), checkfirst=True)

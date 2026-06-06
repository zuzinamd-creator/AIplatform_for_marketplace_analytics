"""password_reset_tokens + backfill report statuses from etl_jobs.

Revision ID: 0026_password_reset_tokens
Revises: 0025_etl_job_file_size
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_password_reset_tokens"
down_revision: str | Sequence[str] | None = "0025_etl_job_file_size"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    # Sync legacy reports.status from latest etl_job per report.
    op.execute(
        """
        UPDATE reports r
        SET status = mapped.report_status::report_status_enum
        FROM (
            SELECT DISTINCT ON (j.report_id)
                j.report_id,
                CASE j.status
                    WHEN 'pending' THEN 'pending'
                    WHEN 'processing' THEN 'processing'
                    WHEN 'completed' THEN 'processed'
                    WHEN 'failed' THEN 'failed'
                    WHEN 'dead_letter' THEN 'failed'
                    ELSE 'pending'
                END AS report_status
            FROM etl_jobs j
            ORDER BY j.report_id, j.created_at DESC
        ) mapped
        WHERE r.id = mapped.report_id AND r.status IS DISTINCT FROM mapped.report_status::report_status_enum
        """
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

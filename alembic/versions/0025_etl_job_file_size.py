"""etl_jobs.file_size_bytes for lightweight-first claim ordering.

Revision ID: 0025_etl_job_file_size
Revises: 0024_fin_ledger_user_op_date
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_etl_job_file_size"
down_revision: str | Sequence[str] | None = "0024_fin_ledger_user_op_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "etl_jobs",
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_etl_jobs_pending_priority",
        "etl_jobs",
        ["status", "file_size_bytes", "created_at"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_etl_jobs_pending_priority", table_name="etl_jobs", if_exists=True)
    op.drop_column("etl_jobs", "file_size_bytes")

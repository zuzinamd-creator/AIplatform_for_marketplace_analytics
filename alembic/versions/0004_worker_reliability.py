"""worker reliability: heartbeat columns and dead_letter status

Revision ID: 0004_worker_reliability
Revises: 0003_queue_isolation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_worker_reliability"
down_revision: str | Sequence[str] | None = "0003_queue_isolation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE job_status_enum ADD VALUE IF NOT EXISTS 'dead_letter'"))

    op.add_column(
        "etl_jobs",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "etl_jobs",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("etl_jobs", "last_heartbeat_at")
    op.drop_column("etl_jobs", "processing_started_at")
    # PostgreSQL does not support removing enum values safely in downgrade.

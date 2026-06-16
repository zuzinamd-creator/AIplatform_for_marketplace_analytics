"""Add physical period_start/period_end columns on reports.

Revision ID: 0031_report_period_columns
Revises: 0030_etl_queue_rls_fix
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_report_period_columns"
down_revision: str | Sequence[str] | None = "0030_etl_queue_rls_fix"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("reports", sa.Column("period_end", sa.Date(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE reports
            SET
              period_start = (NULLIF(raw_data->>'period_start', ''))::date,
              period_end = (NULLIF(raw_data->>'period_end', ''))::date
            WHERE raw_data IS NOT NULL
            """
        )
    )
    op.create_check_constraint(
        "ck_reports_period_range",
        "reports",
        "period_start IS NULL OR period_end IS NULL OR period_end >= period_start",
    )


def downgrade() -> None:
    op.drop_constraint("ck_reports_period_range", "reports", type_="check")
    op.drop_column("reports", "period_end")
    op.drop_column("reports", "period_start")

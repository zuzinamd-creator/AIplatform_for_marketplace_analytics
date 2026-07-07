"""Add promotion_expenses column on reports.

Revision ID: 0033_report_promotion_expenses
Revises: 0032_lockdown_backend_tables
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_report_promotion_expenses"
down_revision: str | Sequence[str] | None = "0032_lockdown_backend_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "promotion_expenses",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_reports_promotion_expenses_nonneg",
        "reports",
        "promotion_expenses >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_reports_promotion_expenses_nonneg", "reports", type_="check")
    op.drop_column("reports", "promotion_expenses")

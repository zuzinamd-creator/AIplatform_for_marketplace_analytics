"""Add jam_subscription_expenses column on reports.

Revision ID: 0036_jam_subscription_expenses
Revises: 0035_registration_invites
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_jam_subscription_expenses"
down_revision: str | Sequence[str] | None = "0035_registration_invites"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reports",
        sa.Column(
            "jam_subscription_expenses",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_reports_jam_subscription_expenses_nonneg",
        "reports",
        "jam_subscription_expenses >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_reports_jam_subscription_expenses_nonneg",
        "reports",
        type_="check",
    )
    op.drop_column("reports", "jam_subscription_expenses")

"""Add users.role for seller / platform_admin (Phase 9.2B).

Revision ID: 0034_user_role_platform_admin
Revises: 0033_report_promotion_expenses
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_user_role_platform_admin"
down_revision: str | Sequence[str] | None = "0033_report_promotion_expenses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORM_ADMIN_EMAIL = "margarita.zuzina@mail.ru"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'seller'"),
        ),
    )
    op.create_check_constraint(
        "ck_users_role_valid",
        "users",
        "role IN ('seller', 'platform_admin')",
    )
    op.execute(
        sa.text(
            "UPDATE users SET role = 'platform_admin' WHERE lower(email) = lower(:email)"
        ).bindparams(email=PLATFORM_ADMIN_EMAIL)
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role_valid", "users", type_="check")
    op.drop_column("users", "role")

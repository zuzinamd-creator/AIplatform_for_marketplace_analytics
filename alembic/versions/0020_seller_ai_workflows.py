"""Seller-facing AI workflow state on recommendations.

Revision ID: 0020_seller_ai_workflows
Revises: 0019_ai_usage_cost_tracking
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_seller_ai_workflows"
down_revision: str | Sequence[str] | None = "0019_ai_usage_cost_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_recommendations"):
        return
    cols = {c["name"] for c in insp.get_columns("ai_recommendations")}
    if "seller_workflow_state" not in cols:
        op.add_column(
            "ai_recommendations",
            sa.Column(
                "seller_workflow_state",
                sa.String(length=32),
                nullable=False,
                server_default="active",
            ),
        )
        op.create_index(
            "ix_ai_recommendations_seller_workflow_state",
            "ai_recommendations",
            ["seller_workflow_state"],
        )
    if "snoozed_until" not in cols:
        op.add_column(
            "ai_recommendations",
            sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_recommendations"):
        return
    cols = {c["name"] for c in insp.get_columns("ai_recommendations")}
    if "snoozed_until" in cols:
        op.drop_column("ai_recommendations", "snoozed_until")
    if "seller_workflow_state" in cols:
        op.drop_index("ix_ai_recommendations_seller_workflow_state", table_name="ai_recommendations")
        op.drop_column("ai_recommendations", "seller_workflow_state")

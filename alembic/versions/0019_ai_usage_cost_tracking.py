"""AI provider usage + cost tracking fields.

Revision ID: 0019_ai_usage_cost_tracking
Revises: 0018_enterprise_autonomous_ops
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_ai_usage_cost_tracking"
down_revision: str | Sequence[str] | None = "0018_enterprise_autonomous_ops"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_execution_runs"):
        return

    cols = {c["name"] for c in insp.get_columns("ai_execution_runs")}
    if "provider_name" not in cols:
        op.add_column(
            "ai_execution_runs",
            sa.Column("provider_name", sa.String(length=64), nullable=True),
        )
    if "model_name" not in cols:
        op.add_column(
            "ai_execution_runs",
            sa.Column("model_name", sa.String(length=128), nullable=True),
        )
    if "prompt_tokens" not in cols:
        op.add_column(
            "ai_execution_runs",
            sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        )
    if "completion_tokens" not in cols:
        op.add_column(
            "ai_execution_runs",
            sa.Column("completion_tokens", sa.Integer(), nullable=True),
        )
    if "estimated_cost" not in cols:
        op.add_column(
            "ai_execution_runs",
            sa.Column("estimated_cost", sa.Numeric(12, 6), nullable=True),
        )


def downgrade() -> None:
    # Best-effort; tolerate missing columns.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_execution_runs"):
        return

    cols = {c["name"] for c in insp.get_columns("ai_execution_runs")}
    for name in ("estimated_cost", "completion_tokens", "prompt_tokens", "model_name", "provider_name"):
        if name in cols:
            op.drop_column("ai_execution_runs", name)


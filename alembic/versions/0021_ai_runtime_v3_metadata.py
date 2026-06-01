"""AI runtime v3 metadata on execution runs.

Revision ID: 0021_ai_runtime_v3_metadata
Revises: 0020_seller_ai_workflows
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_ai_runtime_v3_metadata"
down_revision: str | Sequence[str] | None = "0020_seller_ai_workflows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_execution_runs"):
        return
    cols = {c["name"] for c in insp.get_columns("ai_execution_runs")}
    if "runtime_metadata" not in cols:
        op.add_column(
            "ai_execution_runs",
            sa.Column("runtime_metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_execution_runs"):
        return
    cols = {c["name"] for c in insp.get_columns("ai_execution_runs")}
    if "runtime_metadata" in cols:
        op.drop_column("ai_execution_runs", "runtime_metadata")

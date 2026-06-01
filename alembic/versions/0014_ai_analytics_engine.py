"""AI analytics engine — session memory and insight metadata

Revision ID: 0014_ai_analytics_engine
Revises: 0013_ai_execution_runs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_ai_analytics_engine"
down_revision: str | Sequence[str] | None = "0013_ai_execution_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("ai_session_turns"):
        op.create_table(
            "ai_session_turns",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("session_id", sa.UUID(), nullable=False),
            sa.Column("run_id", sa.UUID(), nullable=True),
            sa.Column("role", sa.String(length=16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["run_id"], ["ai_execution_runs.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_session_turns_session_id", "ai_session_turns", ["session_id"])
        op.create_index("ix_ai_session_turns_user_id", "ai_session_turns", ["user_id"])
        op.execute(sa.text("ALTER TABLE ai_session_turns ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                """
                CREATE POLICY ai_session_turns_tenant_isolation
                ON ai_session_turns
                FOR ALL
                USING (
                    user_id = current_setting('app.current_user_id', true)::uuid
                    OR current_setting('app.queue_role', true)::boolean = true
                    OR current_setting('app.bypass_rls', true)::boolean = true
                )
                WITH CHECK (
                    user_id = current_setting('app.current_user_id', true)::uuid
                    OR current_setting('app.queue_role', true)::boolean = true
                    OR current_setting('app.bypass_rls', true)::boolean = true
                )
                """
            )
        )

    if insp.has_table("ai_insights"):
        cols = {c["name"] for c in insp.get_columns("ai_insights")}
        if "confidence_score" not in cols:
            op.add_column(
                "ai_insights",
                sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
            )
        if "workflow_type" not in cols:
            op.add_column(
                "ai_insights",
                sa.Column("workflow_type", sa.String(length=64), nullable=True),
            )
            op.create_index("ix_ai_insights_workflow_type", "ai_insights", ["workflow_type"])
        if "advisory_metadata" not in cols:
            op.add_column(
                "ai_insights",
                sa.Column("advisory_metadata", sa.dialects.postgresql.JSONB(), nullable=True),
            )


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS ai_session_turns_tenant_isolation ON ai_session_turns"))
    op.drop_index("ix_ai_insights_workflow_type", table_name="ai_insights")
    op.drop_column("ai_insights", "advisory_metadata")
    op.drop_column("ai_insights", "workflow_type")
    op.drop_column("ai_insights", "confidence_score")
    op.drop_index("ix_ai_session_turns_user_id", table_name="ai_session_turns")
    op.drop_index("ix_ai_session_turns_session_id", table_name="ai_session_turns")
    op.drop_table("ai_session_turns")

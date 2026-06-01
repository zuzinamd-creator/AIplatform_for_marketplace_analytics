"""AI intelligence layer — recommendations, strategic memory, feedback

Revision ID: 0017_ai_intelligence_layer
Revises: 0016_production_reliability
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_ai_intelligence_layer"
down_revision: str | Sequence[str] | None = "0016_production_reliability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS = """
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


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("ai_recommendations"):
        op.create_table(
            "ai_recommendations",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("run_id", sa.UUID(), nullable=True),
            sa.Column("insight_id", sa.UUID(), nullable=True),
            sa.Column("parent_recommendation_id", sa.UUID(), nullable=True),
            sa.Column("workflow_type", sa.String(length=64), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "draft",
                    "pending_approval",
                    "approved",
                    "rejected",
                    "superseded",
                    name="recommendation_status_enum",
                ),
                nullable=False,
            ),
            sa.Column(
                "risk_class",
                sa.Enum("low", "medium", "high", "critical", name="recommendation_risk_class_enum"),
                nullable=False,
            ),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
            sa.Column("priority_score", sa.Numeric(8, 4), nullable=True),
            sa.Column("requires_human_approval", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("action_plan", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("evidence_graph", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("reasoning_trace", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("lineage", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("correlation_id", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_recommendations_user_id", "ai_recommendations", ["user_id"])
        op.create_index("ix_ai_recommendations_workflow_type", "ai_recommendations", ["workflow_type"])
        op.execute(sa.text("ALTER TABLE ai_recommendations ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY ai_recommendations_tenant ON ai_recommendations FOR ALL {RLS}"
            )
        )

    if not insp.has_table("ai_strategic_memory"):
        op.create_table(
            "ai_strategic_memory",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("memory_key", sa.String(length=128), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("semantics_version", sa.String(length=16), nullable=False),
            sa.Column("source_run_id", sa.UUID(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ai_strategic_memory_user_key", "ai_strategic_memory", ["user_id", "memory_key"])
        op.execute(sa.text("ALTER TABLE ai_strategic_memory ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(f"CREATE POLICY ai_strategic_memory_tenant ON ai_strategic_memory FOR ALL {RLS}")
        )

    if not insp.has_table("ai_recommendation_feedback"):
        op.create_table(
            "ai_recommendation_feedback",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("recommendation_id", sa.UUID(), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("helpful", sa.Boolean(), nullable=True),
            sa.Column("override_reason", sa.Text(), nullable=True),
            sa.Column("feedback_type", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_ai_recommendation_feedback_rec_id",
            "ai_recommendation_feedback",
            ["recommendation_id"],
        )
        op.execute(sa.text("ALTER TABLE ai_recommendation_feedback ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY ai_recommendation_feedback_tenant ON ai_recommendation_feedback FOR ALL {RLS}"
            )
        )


def downgrade() -> None:
    op.drop_table("ai_recommendation_feedback")
    op.drop_table("ai_strategic_memory")
    op.drop_table("ai_recommendations")

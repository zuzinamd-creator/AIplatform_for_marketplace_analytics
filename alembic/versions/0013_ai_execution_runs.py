"""ai_execution_runs audit table

Revision ID: 0013_ai_execution_runs
Revises: 0012_rebuild_orchestration
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

revision: str = "0013_ai_execution_runs"
down_revision: str | Sequence[str] | None = "0012_rebuild_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_LABELS = ("requested", "running", "succeeded", "failed", "cancelled", "degraded")


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("ai_execution_runs"):
        return

    ensure_pg_enum("ai_execution_status_enum", STATUS_LABELS)
    status_enum = postgresql.ENUM(
        *STATUS_LABELS, name="ai_execution_status_enum", create_type=False
    )

    op.create_table(
        "ai_execution_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("agent_kind", sa.String(length=64), nullable=False),
        sa.Column("status", status_enum, nullable=False, server_default="requested"),
        sa.Column("prompt_id", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("semantics_version", sa.String(length=16), nullable=False),
        sa.Column("context_valid", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("degraded_mode", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("audit_events", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("output_insight_id", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_execution_runs_user_id", "ai_execution_runs", ["user_id"])
    op.create_index("ix_ai_execution_runs_agent_kind", "ai_execution_runs", ["agent_kind"])
    op.create_index(
        "ix_ai_execution_runs_correlation_id",
        "ai_execution_runs",
        ["correlation_id"],
    )

    op.execute(sa.text("ALTER TABLE ai_execution_runs ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY ai_execution_runs_tenant_isolation
            ON ai_execution_runs
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


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS ai_execution_runs_tenant_isolation ON ai_execution_runs"))
    op.drop_index("ix_ai_execution_runs_correlation_id", table_name="ai_execution_runs")
    op.drop_index("ix_ai_execution_runs_agent_kind", table_name="ai_execution_runs")
    op.drop_index("ix_ai_execution_runs_user_id", table_name="ai_execution_runs")
    op.drop_table("ai_execution_runs")
    op.execute(sa.text("DROP TYPE IF EXISTS ai_execution_status_enum"))

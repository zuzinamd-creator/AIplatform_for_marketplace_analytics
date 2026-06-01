"""Enterprise autonomous operations — action journal and schedule policies

Revision ID: 0018_enterprise_autonomous_ops
Revises: 0017_ai_intelligence_layer
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_enterprise_autonomous_ops"
down_revision: str | Sequence[str] | None = "0017_ai_intelligence_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_PLATFORM = """
USING (
    user_id IS NULL AND current_setting('app.queue_role', true)::boolean = true
    OR user_id = current_setting('app.current_user_id', true)::uuid
    OR current_setting('app.bypass_rls', true)::boolean = true
)
WITH CHECK (
    user_id IS NULL AND current_setting('app.queue_role', true)::boolean = true
    OR user_id = current_setting('app.current_user_id', true)::uuid
    OR current_setting('app.bypass_rls', true)::boolean = true
)
"""

RLS_TENANT = """
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

    if not insp.has_table("runtime_autonomous_actions"):
        op.create_table(
            "runtime_autonomous_actions",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("decision_id", sa.String(length=64), nullable=False),
            sa.Column("action_type", sa.String(length=64), nullable=False),
            sa.Column(
                "status",
                sa.Enum(
                    "planned",
                    "executed",
                    "simulated",
                    "blocked",
                    "rolled_back",
                    name="autonomous_action_status_enum",
                ),
                nullable=False,
            ),
            sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("reversible", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("detail", sa.Text(), nullable=False),
            sa.Column("provenance", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("lineage", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("correlation_id", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_runtime_autonomous_actions_user_id", "runtime_autonomous_actions", ["user_id"])
        op.create_index("ix_runtime_autonomous_actions_action_type", "runtime_autonomous_actions", ["action_type"])
        op.execute(sa.text("ALTER TABLE runtime_autonomous_actions ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY runtime_autonomous_actions_rls ON runtime_autonomous_actions FOR ALL {RLS_PLATFORM}"
            )
        )

    if not insp.has_table("runtime_schedule_policies"):
        op.create_table(
            "runtime_schedule_policies",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("maintenance_windows", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("blackout_periods", sa.dialects.postgresql.JSONB(), nullable=True),
            sa.Column("fairness_weight", sa.Float(), nullable=True),
            sa.Column("rebuild_priority_bias", sa.Float(), nullable=True),
            sa.Column("adaptive_rebuild_enabled", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_runtime_schedule_policies_user_id", "runtime_schedule_policies", ["user_id"])
        op.execute(sa.text("ALTER TABLE runtime_schedule_policies ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"CREATE POLICY runtime_schedule_policies_tenant ON runtime_schedule_policies FOR ALL {RLS_TENANT}"
            )
        )


def downgrade() -> None:
    op.drop_table("runtime_schedule_policies")
    op.drop_table("runtime_autonomous_actions")

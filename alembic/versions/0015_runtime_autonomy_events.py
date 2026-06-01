"""Runtime autonomy audit events

Revision ID: 0015_runtime_autonomy_events
Revises: 0014_ai_analytics_engine
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_runtime_autonomy_events"
down_revision: str | Sequence[str] | None = "0014_ai_analytics_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("runtime_autonomy_events"):
        return

    op.create_table(
        "runtime_autonomy_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("reversible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_autonomy_events_user_id",
        "runtime_autonomy_events",
        ["user_id"],
    )
    op.create_index(
        "ix_runtime_autonomy_events_action_type",
        "runtime_autonomy_events",
        ["action_type"],
    )
    op.execute(sa.text("ALTER TABLE runtime_autonomy_events ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY runtime_autonomy_events_tenant_isolation
            ON runtime_autonomy_events
            FOR ALL
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
        )
    )


def downgrade() -> None:
    op.drop_table("runtime_autonomy_events")

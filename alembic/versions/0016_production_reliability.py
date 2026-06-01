"""Production reliability persistence

Revision ID: 0016_production_reliability
Revises: 0015_runtime_autonomy_events
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_production_reliability"
down_revision: str | Sequence[str] | None = "0015_runtime_autonomy_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS_POLICY = """
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


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("runtime_process_heartbeats"):
        op.create_table(
            "runtime_process_heartbeats",
            sa.Column("process_id", sa.UUID(), nullable=False),
            sa.Column("process_kind", sa.String(length=32), nullable=False),
            sa.Column("host", sa.String(length=255), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
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
            sa.PrimaryKeyConstraint("process_id"),
        )
        op.create_index(
            "ix_runtime_process_heartbeats_process_kind",
            "runtime_process_heartbeats",
            ["process_kind"],
        )
        op.execute(sa.text("ALTER TABLE runtime_process_heartbeats ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                """
                CREATE POLICY runtime_process_heartbeats_queue
                ON runtime_process_heartbeats FOR ALL
                USING (current_setting('app.queue_role', true)::boolean = true
                    OR current_setting('app.bypass_rls', true)::boolean = true)
                WITH CHECK (current_setting('app.queue_role', true)::boolean = true
                    OR current_setting('app.bypass_rls', true)::boolean = true)
                """
            )
        )

    if not insp.has_table("runtime_process_leases"):
        op.create_table(
            "runtime_process_leases",
            sa.Column("lease_name", sa.String(length=64), nullable=False),
            sa.Column("holder_id", sa.UUID(), nullable=False),
            sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
            sa.PrimaryKeyConstraint("lease_name"),
        )
        op.create_index(
            "ix_runtime_process_leases_expires_at",
            "runtime_process_leases",
            ["expires_at"],
        )
        op.execute(sa.text("ALTER TABLE runtime_process_leases ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                """
                CREATE POLICY runtime_process_leases_queue
                ON runtime_process_leases FOR ALL
                USING (current_setting('app.queue_role', true)::boolean = true
                    OR current_setting('app.bypass_rls', true)::boolean = true)
                WITH CHECK (current_setting('app.queue_role', true)::boolean = true
                    OR current_setting('app.bypass_rls', true)::boolean = true)
                """
            )
        )

    if not insp.has_table("tenant_containment_states"):
        op.create_table(
            "tenant_containment_states",
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("throttled_until", sa.DateTime(timezone=True), nullable=True),
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
            sa.PrimaryKeyConstraint("user_id"),
        )
        op.execute(sa.text("ALTER TABLE tenant_containment_states ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY tenant_containment_states_tenant
                ON tenant_containment_states FOR ALL
                {RLS_POLICY}
                """
            )
        )

    if not insp.has_table("operator_audit_events"):
        op.create_table(
            "operator_audit_events",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("actor_type", sa.String(length=32), nullable=False),
            sa.Column("action_type", sa.String(length=64), nullable=False),
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
        op.create_index("ix_operator_audit_events_user_id", "operator_audit_events", ["user_id"])
        op.create_index(
            "ix_operator_audit_events_action_type", "operator_audit_events", ["action_type"]
        )
        op.execute(sa.text("ALTER TABLE operator_audit_events ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY operator_audit_events_tenant
                ON operator_audit_events FOR ALL
                {RLS_POLICY}
                """
            )
        )


def downgrade() -> None:
    op.drop_table("operator_audit_events")
    op.drop_table("tenant_containment_states")
    op.drop_table("runtime_process_leases")
    op.drop_table("runtime_process_heartbeats")

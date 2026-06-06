"""auth_audit_events — password change / reset audit trail.

Revision ID: 0027_auth_audit_events
Revises: 0026_password_reset_tokens
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_auth_audit_events"
down_revision: str | Sequence[str] | None = "0026_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RLS = """
USING (
    user_id = current_setting('app.current_user_id', true)::uuid
    OR current_setting('app.bypass_rls', true)::boolean = true
)
WITH CHECK (
    user_id = current_setting('app.current_user_id', true)::uuid
    OR current_setting('app.bypass_rls', true)::boolean = true
)
"""


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("auth_audit_events"):
        return

    op.create_table(
        "auth_audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_audit_events_user_id", "auth_audit_events", ["user_id"])
    op.create_index("ix_auth_audit_events_event_type", "auth_audit_events", ["event_type"])
    op.create_index("ix_auth_audit_events_created_at", "auth_audit_events", ["created_at"])

    op.execute("ALTER TABLE auth_audit_events ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY auth_audit_events_tenant ON auth_audit_events {RLS}")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS auth_audit_events_tenant ON auth_audit_events")
    op.drop_index("ix_auth_audit_events_created_at", table_name="auth_audit_events")
    op.drop_index("ix_auth_audit_events_event_type", table_name="auth_audit_events")
    op.drop_index("ix_auth_audit_events_user_id", table_name="auth_audit_events")
    op.drop_table("auth_audit_events")

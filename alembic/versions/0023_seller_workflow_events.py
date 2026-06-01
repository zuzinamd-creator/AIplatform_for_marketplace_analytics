"""Seller workflow persistence (notes/reminders/history).

Revision ID: 0023_seller_workflow_events
Revises: 0022_sku_unit_economics_daily
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_seller_workflow_events"
down_revision: str | Sequence[str] | None = "0022_sku_unit_economics_daily"
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
    if insp.has_table("seller_workflow_events"):
        return

    op.create_table(
        "seller_workflow_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("recommendation_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["ai_recommendations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seller_workflow_events_user_id", "seller_workflow_events", ["user_id"])
    op.create_index(
        "ix_seller_workflow_events_rec_type",
        "seller_workflow_events",
        ["user_id", "recommendation_id", "event_type"],
    )
    op.create_index(
        "ix_seller_workflow_events_reminder_at",
        "seller_workflow_events",
        ["user_id", "reminder_at"],
    )
    op.execute(sa.text("ALTER TABLE seller_workflow_events ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"CREATE POLICY seller_workflow_events_tenant ON seller_workflow_events FOR ALL {RLS}"))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("seller_workflow_events"):
        return
    op.drop_index("ix_seller_workflow_events_reminder_at", table_name="seller_workflow_events")
    op.drop_index("ix_seller_workflow_events_rec_type", table_name="seller_workflow_events")
    op.drop_index("ix_seller_workflow_events_user_id", table_name="seller_workflow_events")
    op.drop_table("seller_workflow_events")


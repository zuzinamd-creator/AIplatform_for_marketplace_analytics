"""sku unit economics daily projection

Revision ID: 0022_sku_unit_economics_daily
Revises: 0021_ai_runtime_v3_metadata
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_sku_unit_economics_daily"
down_revision: str | Sequence[str] | None = "0021_ai_runtime_v3_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

marketplace_enum = postgresql.ENUM(name="marketplace_enum", create_type=False)


def upgrade() -> None:
    op.create_table(
        "sku_unit_economics_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("units_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("returns_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("payout", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("commissions", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("logistics", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("storage", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("ads", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("penalties", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("acquiring", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("deductions", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("compensation", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("acceptance_fees", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("loyalty_compensation", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("cogs", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("gross_profit", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("contribution_margin", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("margin_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("ad_cost_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("logistics_burden", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("sku", "metric_date", "marketplace", name="uq_sku_unit_econ_daily"),
    )
    op.create_index(
        "ix_sku_unit_econ_daily_tenant_date",
        "sku_unit_economics_daily",
        ["user_id", "metric_date"],
    )

    op.execute(sa.text("ALTER TABLE sku_unit_economics_daily ENABLE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            """
            CREATE POLICY sku_unit_economics_daily_tenant_isolation
            ON sku_unit_economics_daily
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
    op.execute(
        sa.text(
            "DROP POLICY IF EXISTS sku_unit_economics_daily_tenant_isolation ON sku_unit_economics_daily"
        )
    )
    op.execute(sa.text("ALTER TABLE sku_unit_economics_daily DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_sku_unit_econ_daily_tenant_date", table_name="sku_unit_economics_daily")
    op.drop_table("sku_unit_economics_daily")


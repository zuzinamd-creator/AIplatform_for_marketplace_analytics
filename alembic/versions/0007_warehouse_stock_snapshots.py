"""warehouse stock snapshots and loss analytics storage

Revision ID: 0007_warehouse_stock_snapshots
Revises: 0006_inventory_ledger
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_warehouse_stock_snapshots"
down_revision: str | Sequence[str] | None = "0006_inventory_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SNAPSHOT_TENANT_TABLES = ("warehouse_stock_snapshots",)


def upgrade() -> None:
    op.create_table(
        "warehouse_stock_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("nm_id", sa.String(length=64), nullable=True),
        sa.Column("warehouse_name", sa.String(length=256), nullable=True),
        sa.Column("opening_stock", sa.Integer(), nullable=False),
        sa.Column("inbound_units", sa.Integer(), nullable=False),
        sa.Column("sold_units", sa.Integer(), nullable=False),
        sa.Column("returned_units", sa.Integer(), nullable=False),
        sa.Column("lost_units", sa.Integer(), nullable=False),
        sa.Column("writeoff_units", sa.Integer(), nullable=False),
        sa.Column("expected_closing_stock", sa.Integer(), nullable=False),
        sa.Column("actual_stock", sa.Integer(), nullable=False),
        sa.Column("discrepancy_units", sa.Integer(), nullable=False),
        sa.Column("discrepancy_cost", sa.Numeric(18, 4), nullable=False),
        sa.Column("discrepancy_sale_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "snapshot_date",
            "sku",
            "warehouse_name",
            name="uq_warehouse_stock_snapshot_day_sku_wh",
        ),
    )
    op.create_index("ix_warehouse_stock_snapshots_user_id", "warehouse_stock_snapshots", ["user_id"])
    op.create_index(
        "ix_warehouse_stock_snapshots_snapshot_date",
        "warehouse_stock_snapshots",
        ["snapshot_date"],
    )
    op.create_index("ix_warehouse_stock_snapshots_sku", "warehouse_stock_snapshots", ["sku"])
    op.create_index(
        "ix_warehouse_stock_snapshots_warehouse_name",
        "warehouse_stock_snapshots",
        ["warehouse_name"],
    )
    op.create_index(
        "ix_warehouse_stock_snapshots_discrepancy_units",
        "warehouse_stock_snapshots",
        ["discrepancy_units"],
    )

    for table_name in SNAPSHOT_TENANT_TABLES:
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_tenant_isolation
                ON {table_name}
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
    for table_name in reversed(SNAPSHOT_TENANT_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
    op.drop_index(
        "ix_warehouse_stock_snapshots_discrepancy_units",
        table_name="warehouse_stock_snapshots",
    )
    op.drop_index(
        "ix_warehouse_stock_snapshots_warehouse_name",
        table_name="warehouse_stock_snapshots",
    )
    op.drop_index("ix_warehouse_stock_snapshots_sku", table_name="warehouse_stock_snapshots")
    op.drop_index(
        "ix_warehouse_stock_snapshots_snapshot_date",
        table_name="warehouse_stock_snapshots",
    )
    op.drop_index("ix_warehouse_stock_snapshots_user_id", table_name="warehouse_stock_snapshots")
    op.drop_table("warehouse_stock_snapshots")

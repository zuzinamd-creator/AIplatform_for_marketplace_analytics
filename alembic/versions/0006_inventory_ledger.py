"""inventory ledger foundation

Revision ID: 0006_inventory_ledger
Revises: 0005_wb_financial_platform
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

revision: str = "0006_inventory_ledger"
down_revision: str | Sequence[str] | None = "0005_wb_financial_platform"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

inventory_operation_type_enum = postgresql.ENUM(
    "inbound",
    "sale",
    "return",
    "logistics_loss",
    "warehouse_loss",
    "defect",
    "writeoff",
    "transfer",
    "compensation",
    "inventory_adjustment",
    name="inventory_operation_type_enum",
    create_type=False,
)

INVENTORY_TENANT_TABLES = ("inventory_ledger_entries",)


def upgrade() -> None:
    ensure_pg_enum(
        "inventory_operation_type_enum",
        (
            "inbound",
            "sale",
            "return",
            "logistics_loss",
            "warehouse_loss",
            "defect",
            "writeoff",
            "transfer",
            "compensation",
            "inventory_adjustment",
        ),
    )

    op.create_table(
        "inventory_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("nm_id", sa.String(length=64), nullable=True),
        sa.Column("warehouse_name", sa.String(length=256), nullable=True),
        sa.Column("operation_type", inventory_operation_type_enum, nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("cost_per_unit", sa.Numeric(18, 4), nullable=True),
        sa.Column("sale_price_per_unit", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_cost_delta", sa.Numeric(18, 4), nullable=False),
        sa.Column("total_sale_delta", sa.Numeric(18, 4), nullable=False),
        sa.Column("source_row_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "report_id",
            "source_row_id",
            "operation_type",
            name="uq_inventory_ledger_report_source_operation",
        ),
    )
    op.create_index("ix_inventory_ledger_entries_user_id", "inventory_ledger_entries", ["user_id"])
    op.create_index("ix_inventory_ledger_entries_report_id", "inventory_ledger_entries", ["report_id"])
    op.create_index(
        "ix_inventory_ledger_entries_operation_date",
        "inventory_ledger_entries",
        ["operation_date"],
    )
    op.create_index("ix_inventory_ledger_entries_sku", "inventory_ledger_entries", ["sku"])
    op.create_index(
        "ix_inventory_ledger_entries_warehouse_name",
        "inventory_ledger_entries",
        ["warehouse_name"],
    )
    op.create_index(
        "ix_inventory_ledger_entries_operation_type",
        "inventory_ledger_entries",
        ["operation_type"],
    )

    for table_name in INVENTORY_TENANT_TABLES:
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
    for table_name in reversed(INVENTORY_TENANT_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_inventory_ledger_entries_operation_type", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_entries_warehouse_name", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_entries_sku", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_entries_operation_date", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_entries_report_id", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_entries_user_id", table_name="inventory_ledger_entries")
    op.drop_table("inventory_ledger_entries")
    inventory_operation_type_enum.drop(op.get_bind(), checkfirst=True)

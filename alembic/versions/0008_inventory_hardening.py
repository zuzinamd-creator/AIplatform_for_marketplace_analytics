"""inventory subsystem hardening: semantics version and rebuild indexes

Revision ID: 0008_inventory_hardening
Revises: 0007_warehouse_stock_snapshots
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_inventory_hardening"
down_revision: str | Sequence[str] | None = "0007_warehouse_stock_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "normalized_report_rows",
        sa.Column("semantics_version", sa.String(length=16), nullable=False, server_default="1.0"),
    )
    op.add_column(
        "inventory_ledger_entries",
        sa.Column("semantics_version", sa.String(length=16), nullable=False, server_default="1.0"),
    )
    op.alter_column("normalized_report_rows", "semantics_version", server_default=None)
    op.alter_column("inventory_ledger_entries", "semantics_version", server_default=None)

    op.create_index(
        "ix_inventory_ledger_user_operation_date",
        "inventory_ledger_entries",
        ["user_id", "operation_date"],
    )
    op.create_index(
        "ix_inventory_ledger_user_sku",
        "inventory_ledger_entries",
        ["user_id", "sku"],
    )
    op.create_index(
        "ix_inventory_ledger_user_warehouse",
        "inventory_ledger_entries",
        ["user_id", "warehouse_name"],
    )
    op.create_index(
        "ix_warehouse_snapshots_user_snapshot_date",
        "warehouse_stock_snapshots",
        ["user_id", "snapshot_date"],
    )
    op.create_index(
        "ix_warehouse_snapshots_user_sku",
        "warehouse_stock_snapshots",
        ["user_id", "sku"],
    )
    op.create_index(
        "ix_warehouse_snapshots_user_warehouse",
        "warehouse_stock_snapshots",
        ["user_id", "warehouse_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_warehouse_snapshots_user_warehouse", table_name="warehouse_stock_snapshots")
    op.drop_index("ix_warehouse_snapshots_user_sku", table_name="warehouse_stock_snapshots")
    op.drop_index("ix_warehouse_snapshots_user_snapshot_date", table_name="warehouse_stock_snapshots")
    op.drop_index("ix_inventory_ledger_user_warehouse", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_user_sku", table_name="inventory_ledger_entries")
    op.drop_index("ix_inventory_ledger_user_operation_date", table_name="inventory_ledger_entries")
    op.drop_column("inventory_ledger_entries", "semantics_version")
    op.drop_column("normalized_report_rows", "semantics_version")

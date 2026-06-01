"""inventory stabilization: idempotent composite indexes for rebuild paths

Revision ID: 0009_inventory_stabilization
Revises: 0008_inventory_hardening
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_inventory_stabilization"
down_revision: str | Sequence[str] | None = "0008_inventory_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Idempotent with 0008 — safe when indexes already exist from a prior deploy.
_COMPOSITE_INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    (
        "ix_inventory_ledger_user_operation_date",
        "inventory_ledger_entries",
        ["user_id", "operation_date"],
    ),
    ("ix_inventory_ledger_user_sku", "inventory_ledger_entries", ["user_id", "sku"]),
    (
        "ix_inventory_ledger_user_warehouse",
        "inventory_ledger_entries",
        ["user_id", "warehouse_name"],
    ),
    (
        "ix_warehouse_snapshots_user_snapshot_date",
        "warehouse_stock_snapshots",
        ["user_id", "snapshot_date"],
    ),
    ("ix_warehouse_snapshots_user_sku", "warehouse_stock_snapshots", ["user_id", "sku"]),
    (
        "ix_warehouse_snapshots_user_warehouse",
        "warehouse_stock_snapshots",
        ["user_id", "warehouse_name"],
    ),
)


def upgrade() -> None:
    for name, table, columns in _COMPOSITE_INDEXES:
        op.create_index(name, table, columns, if_not_exists=True)


def downgrade() -> None:
    # Indexes are owned by the inventory hardening chain; retained for production safety.
    pass

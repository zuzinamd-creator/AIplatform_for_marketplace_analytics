"""Covering index for Safe Incremental Stream v1 inventory rebuild.

Revision ID: 0037_inv_stream_idx
Revises: 0036_jam_subscription_expenses
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0037_inv_stream_idx"
down_revision: str | Sequence[str] | None = "0036_jam_subscription_expenses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_inventory_ledger_stream_order"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "inventory_ledger_entries",
        [
            "user_id",
            "sku",
            "warehouse_name",
            "operation_date",
            "created_at",
            "source_row_id",
        ],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="inventory_ledger_entries", if_exists=True)

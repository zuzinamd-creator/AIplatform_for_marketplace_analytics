"""Composite index for financial ledger rebuild and period scans.

Revision ID: 0024_fin_ledger_user_op_date
Revises: 0023_seller_workflow_events
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024_fin_ledger_user_op_date"
down_revision: str | Sequence[str] | None = "0023_seller_workflow_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_financial_ledger_user_operation_date",
        "financial_ledger_entries",
        ["user_id", "operation_date"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_financial_ledger_user_operation_date",
        table_name="financial_ledger_entries",
        if_exists=True,
    )

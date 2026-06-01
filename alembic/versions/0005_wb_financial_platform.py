"""wb financial data platform tables

Revision ID: 0005_wb_financial_platform
Revises: 0004_worker_reliability
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

revision: str = "0005_wb_financial_platform"
down_revision: str | Sequence[str] | None = "0004_worker_reliability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ledger_operation_type_enum = postgresql.ENUM(
    "sale",
    "return",
    "logistics",
    "storage_fee",
    "commission",
    "penalty",
    "acquiring",
    "compensation",
    "payout",
    "deduction",
    "advertisement",
    "other",
    name="ledger_operation_type_enum",
    create_type=False,
)

marketplace_enum = postgresql.ENUM(name="marketplace_enum", create_type=False)

FINANCE_TENANT_TABLES = (
    "raw_reports",
    "normalized_report_rows",
    "financial_ledger_entries",
    "daily_aggregates",
    "sku_daily_metrics",
    "report_reconciliations",
)


def upgrade() -> None:
    ensure_pg_enum(
        "ledger_operation_type_enum",
        (
            "sale",
            "return",
            "logistics",
            "storage_fee",
            "commission",
            "penalty",
            "acquiring",
            "compensation",
            "payout",
            "deduction",
            "advertisement",
            "other",
        ),
    )

    op.add_column(
        "cost_history",
        sa.Column("product_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
    )
    op.add_column(
        "cost_history",
        sa.Column("packaging_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
    )
    op.add_column(
        "cost_history",
        sa.Column("inbound_logistics_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
    )
    op.add_column(
        "cost_history",
        sa.Column("additional_cost", sa.Numeric(14, 4), nullable=False, server_default="0"),
    )
    op.add_column("cost_history", sa.Column("comment", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE cost_history SET product_cost = cost"))

    op.create_table(
        "raw_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("file_checksum", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("ingest_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("report_id", name="uq_raw_report_report_id"),
    )

    op.create_table(
        "normalized_report_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_row_id", sa.String(length=128), nullable=False),
        sa.Column("source_row_index", sa.Integer(), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("nm_id", sa.String(length=64), nullable=True),
        sa.Column("canonical_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("report_id", "source_row_id", name="uq_normalized_report_source_row"),
    )

    op.create_table(
        "financial_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("normalized_row_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("nm_id", sa.String(length=64), nullable=True),
        sa.Column("operation_type", ledger_operation_type_enum, nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_row_id", sa.String(length=128), nullable=False),
        sa.Column("entry_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["normalized_row_id"], ["normalized_report_rows.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("report_id", "source_row_id", name="uq_ledger_report_source_row"),
    )

    op.create_table(
        "daily_aggregates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_date", sa.Date(), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_profit", sa.Numeric(18, 4), nullable=False),
        sa.Column("margin", sa.Numeric(10, 4), nullable=True),
        sa.Column("roi", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("buyout_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("average_check", sa.Numeric(18, 4), nullable=True),
        sa.Column("units_sold", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("aggregate_date", "marketplace", name="uq_daily_aggregate_day_marketplace"),
    )

    op.create_table(
        "sku_daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_profit", sa.Numeric(18, 4), nullable=False),
        sa.Column("margin", sa.Numeric(10, 4), nullable=True),
        sa.Column("roi", sa.Numeric(10, 4), nullable=True),
        sa.Column("return_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("buyout_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("average_check", sa.Numeric(18, 4), nullable=True),
        sa.Column("units_sold", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("sku", "metric_date", "marketplace", name="uq_sku_daily_metric"),
    )

    op.create_table(
        "report_reconciliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gross_revenue", sa.Numeric(18, 4), nullable=False),
        sa.Column("net_revenue", sa.Numeric(18, 4), nullable=False),
        sa.Column("wb_commissions", sa.Numeric(18, 4), nullable=False),
        sa.Column("logistics", sa.Numeric(18, 4), nullable=False),
        sa.Column("deductions", sa.Numeric(18, 4), nullable=False),
        sa.Column("returns_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("expected_payout", sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_payout", sa.Numeric(18, 4), nullable=False),
        sa.Column("difference", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("report_id", name="uq_report_reconciliation_report_id"),
    )

    for table_name in FINANCE_TENANT_TABLES:
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
    for table_name in reversed(FINANCE_TENANT_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))
        op.drop_table(table_name)

    op.drop_column("cost_history", "comment")
    op.drop_column("cost_history", "additional_cost")
    op.drop_column("cost_history", "inbound_logistics_cost")
    op.drop_column("cost_history", "packaging_cost")
    op.drop_column("cost_history", "product_cost")
    ledger_operation_type_enum.drop(op.get_bind(), checkfirst=True)

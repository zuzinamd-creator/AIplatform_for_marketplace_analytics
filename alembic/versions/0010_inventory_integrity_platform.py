"""inventory integrity platform: staging, drift checks, anomalies

Revision ID: 0010_inventory_integrity
Revises: 0009_inventory_stabilization
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

revision: str = "0010_inventory_integrity"
down_revision: str | Sequence[str] | None = "0009_inventory_stabilization"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ANOMALY_LABELS = (
    "snapshot_drift",
    "semantics_version_missing",
    "inconsistent_opening_balance",
    "rebuild_gap",
    "negative_inventory",
    "checksum_mismatch",
)

INTEGRITY_TABLES = (
    "warehouse_stock_snapshots_staging",
    "snapshot_consistency_checks",
    "inventory_integrity_anomalies",
)


def upgrade() -> None:
    ensure_pg_enum("inventory_integrity_anomaly_type_enum", ANOMALY_LABELS)
    anomaly_enum = postgresql.ENUM(
        *ANOMALY_LABELS,
        name="inventory_integrity_anomaly_type_enum",
        create_type=False,
    )

    op.add_column(
        "warehouse_stock_snapshots",
        sa.Column("semantics_version", sa.String(length=16), nullable=False, server_default="1.0"),
    )
    op.alter_column("warehouse_stock_snapshots", "semantics_version", server_default=None)

    op.create_table(
        "warehouse_stock_snapshots_staging",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rebuild_run_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("semantics_version", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_wh_snapshots_staging_user_run",
        "warehouse_stock_snapshots_staging",
        ["user_id", "rebuild_run_id"],
    )

    op.create_table(
        "snapshot_consistency_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("warehouse_name", sa.String(length=256), nullable=True),
        sa.Column("ledger_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("semantics_version", sa.String(length=16), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_consistent", sa.Boolean(), nullable=False),
        sa.Column("mismatch_details", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_snapshot_consistency_user_checked",
        "snapshot_consistency_checks",
        ["user_id", "checked_at"],
    )

    op.create_table(
        "inventory_integrity_anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anomaly_type", anomaly_enum, nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("sku", sa.String(length=128), nullable=True),
        sa.Column("warehouse_name", sa.String(length=256), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_inventory_anomalies_user_detected",
        "inventory_integrity_anomalies",
        ["user_id", "detected_at"],
    )

    for table_name in INTEGRITY_TABLES:
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
    for table_name in reversed(INTEGRITY_TABLES):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"))
        op.drop_table(table_name)
    op.drop_column("warehouse_stock_snapshots", "semantics_version")
    op.execute(sa.text("DROP TYPE IF EXISTS inventory_integrity_anomaly_type_enum"))

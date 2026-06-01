"""operability: etl anomalies; semantics governance tables

Revision ID: 0011_operability_semantics
Revises: 0010_inventory_integrity
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

revision: str = "0011_operability_semantics"
down_revision: str | Sequence[str] | None = "0010_inventory_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEVERITY_LABELS = ("info", "warning", "error", "critical")
PARSER_STAGE_LABELS = (
    "load",
    "parse",
    "normalize",
    "ledger",
    "inventory",
    "persist",
    "rebuild",
    "verification",
)
ANOMALY_TYPE_LABELS = (
    "negative_inventory",
    "impossible_warehouse_transition",
    "future_dated_operation",
    "duplicate_replay",
    "invalid_decimal_coercion",
    "unsupported_semantics",
    "snapshot_mismatch",
    "parse_error",
    "validation_warning",
    "checksum_mismatch",
    "semantics_ingest_blocked",
    "semantics_rebuild_blocked",
)
LIFECYCLE_STATUS_LABELS = ("active", "deprecated", "disabled")

RLS_TABLES = (
    "etl_anomalies",
    "semantics_lifecycle_versions",
    "snapshot_rebuild_requirements",
    "semantics_change_log",
)


def upgrade() -> None:
    for name, labels in (
        ("etl_anomaly_severity_enum", SEVERITY_LABELS),
        ("etl_parser_stage_enum", PARSER_STAGE_LABELS),
        ("etl_anomaly_type_enum", ANOMALY_TYPE_LABELS),
        ("semantics_lifecycle_status_enum", LIFECYCLE_STATUS_LABELS),
    ):
        ensure_pg_enum(name, labels)

    severity_enum = postgresql.ENUM(*SEVERITY_LABELS, name="etl_anomaly_severity_enum", create_type=False)
    stage_enum = postgresql.ENUM(*PARSER_STAGE_LABELS, name="etl_parser_stage_enum", create_type=False)
    anomaly_enum = postgresql.ENUM(*ANOMALY_TYPE_LABELS, name="etl_anomaly_type_enum", create_type=False)
    lifecycle_enum = postgresql.ENUM(
        *LIFECYCLE_STATUS_LABELS, name="semantics_lifecycle_status_enum", create_type=False
    )

    op.create_table(
        "etl_anomalies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_file_name", sa.String(length=512), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("severity", severity_enum, nullable=False),
        sa.Column("anomaly_type", anomaly_enum, nullable=False),
        sa.Column("parser_stage", stage_enum, nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column("normalized_payload", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("semantics_version", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_etl_anomalies_user_created", "etl_anomalies", ["user_id", "created_at"])
    op.create_index("ix_etl_anomalies_report", "etl_anomalies", ["report_id"])

    op.create_table(
        "semantics_lifecycle_versions",
        sa.Column("version", sa.String(length=16), primary_key=True, nullable=False),
        sa.Column("status", lifecycle_enum, nullable=False),
        sa.Column("introduced_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supported_for_rebuild", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("supported_for_ingest", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO semantics_lifecycle_versions
                (version, status, supported_for_rebuild, supported_for_ingest, notes)
            VALUES
                ('1.0', 'active', true, true, 'Initial frozen WB realization semantics')
            ON CONFLICT (version) DO NOTHING
            """
        )
    )

    op.create_table(
        "snapshot_rebuild_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("semantics_version", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requires_rebuild", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["semantics_version"],
            ["semantics_lifecycle_versions.version"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_snapshot_rebuild_req_user_version",
        "snapshot_rebuild_requirements",
        ["user_id", "semantics_version"],
    )

    op.create_table(
        "semantics_change_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("old_version", sa.String(length=16), nullable=True),
        sa.Column("new_version", sa.String(length=16), nullable=False),
        sa.Column("changed_operations", postgresql.JSONB(), nullable=True),
        sa.Column("migration_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    for table_name in RLS_TABLES:
        if table_name == "semantics_lifecycle_versions" or table_name == "semantics_change_log":
            continue
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
    for table_name in (
        "snapshot_rebuild_requirements",
        "etl_anomalies",
        "semantics_change_log",
        "semantics_lifecycle_versions",
    ):
        if table_name in ("etl_anomalies", "snapshot_rebuild_requirements"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"))
        op.drop_table(table_name)
    op.execute(sa.text("DROP TYPE IF EXISTS semantics_lifecycle_status_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS etl_anomaly_type_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS etl_parser_stage_enum"))
    op.execute(sa.text("DROP TYPE IF EXISTS etl_anomaly_severity_enum"))

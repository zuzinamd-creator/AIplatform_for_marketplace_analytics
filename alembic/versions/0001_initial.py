"""initial async schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-25 21:23:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migrations_support.pg_enum import ensure_pg_enum
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


marketplace_enum = postgresql.ENUM(
    "wildberries",
    "ozon",
    "costs",
    name="marketplace_enum",
    create_type=False,
)
report_type_enum = postgresql.ENUM(
    "sales",
    "orders",
    "stock",
    "finance",
    "costs",
    "other",
    name="report_type_enum",
    create_type=False,
)
report_status_enum = postgresql.ENUM(
    "pending",
    "uploaded",
    "processing",
    "processed",
    "failed",
    name="report_status_enum",
    create_type=False,
)
metric_period_enum = postgresql.ENUM(
    "daily",
    "weekly",
    "monthly",
    name="metric_period_enum",
    create_type=False,
)
insight_status_enum = postgresql.ENUM(
    "pending",
    "ready",
    "archived",
    name="insight_status_enum",
    create_type=False,
)

TENANT_TABLES = (
    "reports",
    "products",
    "metrics",
    "sku_mapping",
    "cost_history",
    "ai_insights",
)


def upgrade() -> None:
    ensure_pg_enum("marketplace_enum", ("wildberries", "ozon", "costs"))
    ensure_pg_enum(
        "report_type_enum",
        ("sales", "orders", "stock", "finance", "costs", "other"),
    )
    ensure_pg_enum(
        "report_status_enum",
        ("pending", "uploaded", "processing", "processed", "failed"),
    )
    ensure_pg_enum("metric_period_enum", ("daily", "weekly", "monthly"))
    ensure_pg_enum("insight_status_enum", ("pending", "ready", "archived"))

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("report_type", report_type_enum, nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("status", report_status_enum, nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_reports_user_id"), "reports", ["user_id"], unique=False)
    op.create_index(op.f("ix_reports_idempotency_key"), "reports", ["idempotency_key"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("external_sku", sa.String(length=128), nullable=False),
        sa.Column("internal_sku", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "marketplace", "external_sku", name="uq_product_tenant_sku"),
    )
    op.create_index(op.f("ix_products_user_id"), "products", ["user_id"], unique=False)
    op.create_index(op.f("ix_products_external_sku"), "products", ["external_sku"], unique=False)
    op.create_index(op.f("ix_products_internal_sku"), "products", ["internal_sku"], unique=False)

    op.create_table(
        "sku_mapping",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("internal_sku", sa.String(length=128), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("marketplace_sku", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "marketplace", "marketplace_sku", name="uq_sku_mapping_tenant_mp_sku"),
    )
    op.create_index(op.f("ix_sku_mapping_user_id"), "sku_mapping", ["user_id"], unique=False)
    op.create_index(op.f("ix_sku_mapping_internal_sku"), "sku_mapping", ["internal_sku"], unique=False)
    op.create_index(op.f("ix_sku_mapping_marketplace_sku"), "sku_mapping", ["marketplace_sku"], unique=False)

    op.create_table(
        "cost_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("internal_sku", sa.String(length=128), nullable=False),
        sa.Column("cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_cost_history_user_id"), "cost_history", ["user_id"], unique=False)
    op.create_index(op.f("ix_cost_history_internal_sku"), "cost_history", ["internal_sku"], unique=False)
    op.create_index(op.f("ix_cost_history_effective_from"), "cost_history", ["effective_from"], unique=False)

    op.create_table(
        "metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("internal_sku", sa.String(length=128), nullable=False),
        sa.Column("marketplace", marketplace_enum, nullable=False),
        sa.Column("period", metric_period_enum, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("revenue", sa.Numeric(14, 2), nullable=True),
        sa.Column("orders_count", sa.Integer(), nullable=True),
        sa.Column("units_sold", sa.Integer(), nullable=True),
        sa.Column("margin", sa.Numeric(14, 2), nullable=True),
        sa.Column("kpi_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id",
            "internal_sku",
            "marketplace",
            "period",
            "period_start",
            name="uq_metric_tenant_period",
        ),
    )
    op.create_index(op.f("ix_metrics_user_id"), "metrics", ["user_id"], unique=False)
    op.create_index(op.f("ix_metrics_internal_sku"), "metrics", ["internal_sku"], unique=False)
    op.create_index(op.f("ix_metrics_period_start"), "metrics", ["period_start"], unique=False)

    op.create_table(
        "ai_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("insight_type", sa.String(length=64), nullable=False),
        sa.Column("status", insight_status_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("context_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_metric_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_ai_insights_user_id"), "ai_insights", ["user_id"], unique=False)
    op.create_index(op.f("ix_ai_insights_insight_type"), "ai_insights", ["insight_type"], unique=False)

    for table_name in TENANT_TABLES:
        op.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {table_name}_tenant_isolation
                ON {table_name}
                FOR ALL
                USING (
                    user_id = current_setting('app.current_user_id')::uuid
                    OR current_setting('app.bypass_rls', true)::boolean = true
                )
                WITH CHECK (
                    user_id = current_setting('app.current_user_id')::uuid
                    OR current_setting('app.bypass_rls', true)::boolean = true
                )
                """
            )
        )


def downgrade() -> None:
    for table_name in TENANT_TABLES:
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table_name}_tenant_isolation ON {table_name}"))
        op.execute(sa.text(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"))

    op.drop_index(op.f("ix_ai_insights_insight_type"), table_name="ai_insights")
    op.drop_index(op.f("ix_ai_insights_user_id"), table_name="ai_insights")
    op.drop_table("ai_insights")

    op.drop_index(op.f("ix_metrics_period_start"), table_name="metrics")
    op.drop_index(op.f("ix_metrics_internal_sku"), table_name="metrics")
    op.drop_index(op.f("ix_metrics_user_id"), table_name="metrics")
    op.drop_table("metrics")

    op.drop_index(op.f("ix_cost_history_effective_from"), table_name="cost_history")
    op.drop_index(op.f("ix_cost_history_internal_sku"), table_name="cost_history")
    op.drop_index(op.f("ix_cost_history_user_id"), table_name="cost_history")
    op.drop_table("cost_history")

    op.drop_index(op.f("ix_sku_mapping_marketplace_sku"), table_name="sku_mapping")
    op.drop_index(op.f("ix_sku_mapping_internal_sku"), table_name="sku_mapping")
    op.drop_index(op.f("ix_sku_mapping_user_id"), table_name="sku_mapping")
    op.drop_table("sku_mapping")

    op.drop_index(op.f("ix_products_internal_sku"), table_name="products")
    op.drop_index(op.f("ix_products_external_sku"), table_name="products")
    op.drop_index(op.f("ix_products_user_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_reports_idempotency_key"), table_name="reports")
    op.drop_index(op.f("ix_reports_user_id"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    insight_status_enum.drop(op.get_bind(), checkfirst=True)
    metric_period_enum.drop(op.get_bind(), checkfirst=True)
    report_status_enum.drop(op.get_bind(), checkfirst=True)
    report_type_enum.drop(op.get_bind(), checkfirst=True)
    marketplace_enum.drop(op.get_bind(), checkfirst=True)

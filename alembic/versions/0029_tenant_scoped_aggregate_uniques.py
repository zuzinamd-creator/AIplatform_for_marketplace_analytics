"""Scope aggregate unique constraints per tenant (user_id).

Revision ID: 0029_tenant_aggregate_uniques
Revises: 0028_force_rls_marketplace_app
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_tenant_aggregate_uniques"
down_revision: str | Sequence[str] | None = "0028_force_rls_marketplace_app"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_daily_aggregate_day_marketplace", "daily_aggregates", type_="unique")
    op.create_unique_constraint(
        "uq_daily_aggregate_day_marketplace",
        "daily_aggregates",
        ["user_id", "aggregate_date", "marketplace"],
    )

    op.drop_constraint("uq_sku_daily_metric", "sku_daily_metrics", type_="unique")
    op.create_unique_constraint(
        "uq_sku_daily_metric",
        "sku_daily_metrics",
        ["user_id", "sku", "metric_date", "marketplace"],
    )

    op.drop_constraint("uq_sku_unit_econ_daily", "sku_unit_economics_daily", type_="unique")
    op.create_unique_constraint(
        "uq_sku_unit_econ_daily",
        "sku_unit_economics_daily",
        ["user_id", "sku", "metric_date", "marketplace"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_sku_unit_econ_daily", "sku_unit_economics_daily", type_="unique")
    op.create_unique_constraint(
        "uq_sku_unit_econ_daily",
        "sku_unit_economics_daily",
        ["sku", "metric_date", "marketplace"],
    )

    op.drop_constraint("uq_sku_daily_metric", "sku_daily_metrics", type_="unique")
    op.create_unique_constraint(
        "uq_sku_daily_metric",
        "sku_daily_metrics",
        ["sku", "metric_date", "marketplace"],
    )

    op.drop_constraint("uq_daily_aggregate_day_marketplace", "daily_aggregates", type_="unique")
    op.create_unique_constraint(
        "uq_daily_aggregate_day_marketplace",
        "daily_aggregates",
        ["aggregate_date", "marketplace"],
    )

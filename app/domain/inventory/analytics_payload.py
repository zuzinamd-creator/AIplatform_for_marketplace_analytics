from __future__ import annotations

from app.domain.inventory.snapshot_types import InventoryLossAnalytics
from app.etl.types import AnalyticsPayload


def extend_analytics_payload(
    payload: dict,
    *,
    loss_analytics: InventoryLossAnalytics | None,
) -> AnalyticsPayload:
    """Add inventory loss fields without breaking existing analytics keys."""
    if loss_analytics is None:
        return payload  # type: ignore[return-value]

    extended = dict(payload)
    extended["inventory_losses_units"] = loss_analytics.inventory_losses_units
    extended["inventory_losses_cost"] = str(loss_analytics.inventory_losses_cost)
    extended["inventory_losses_sale_value"] = str(loss_analytics.inventory_losses_sale_value)
    extended["warehouse_discrepancies"] = [
        {
            "sku": item.sku,
            "nm_id": item.nm_id,
            "warehouse_name": item.warehouse_name,
            "snapshot_date": item.snapshot_date.isoformat(),
            "discrepancy_units": item.discrepancy_units,
            "discrepancy_cost": str(item.discrepancy_cost),
            "discrepancy_sale_value": str(item.discrepancy_sale_value),
        }
        for item in loss_analytics.warehouse_discrepancies
    ]
    extended["top_loss_skus"] = [
        {"sku": sku, "loss_cost": str(cost)} for sku, cost in loss_analytics.top_loss_skus
    ]
    return extended  # type: ignore[return-value]

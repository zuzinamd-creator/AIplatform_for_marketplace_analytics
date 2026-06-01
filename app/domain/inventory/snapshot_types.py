from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class WarehouseStockSnapshotDraft:
    snapshot_date: date
    sku: str | None
    nm_id: str | None
    warehouse_name: str | None
    opening_stock: int
    inbound_units: int
    sold_units: int
    returned_units: int
    lost_units: int
    writeoff_units: int
    expected_closing_stock: int
    actual_stock: int
    discrepancy_units: int
    discrepancy_cost: Decimal
    discrepancy_sale_value: Decimal
    semantics_version: str = "1.0"


@dataclass(frozen=True)
class WarehouseDiscrepancySummary:
    sku: str | None
    nm_id: str | None
    warehouse_name: str | None
    snapshot_date: date
    discrepancy_units: int
    discrepancy_cost: Decimal
    discrepancy_sale_value: Decimal


@dataclass(frozen=True)
class InventoryLossAnalytics:
    inventory_losses_units: int
    inventory_losses_cost: Decimal
    inventory_losses_sale_value: Decimal
    warehouse_discrepancies: list[WarehouseDiscrepancySummary]
    top_loss_skus: list[tuple[str, Decimal]]

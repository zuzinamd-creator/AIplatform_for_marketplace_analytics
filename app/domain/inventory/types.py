from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.models.inventory.enums import InventoryOperationType


@dataclass(frozen=True)
class InventoryMovementDraft:
    operation_date: date
    sku: str | None
    nm_id: str | None
    warehouse_name: str | None
    operation_type: InventoryOperationType
    quantity_delta: int
    cost_per_unit: Decimal | None
    sale_price_per_unit: Decimal | None
    total_cost_delta: Decimal
    total_sale_delta: Decimal
    source_row_id: str
    semantics_version: str
    canonical_payload: dict[str, object]
    raw_payload: dict[str, str]

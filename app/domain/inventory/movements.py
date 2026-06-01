from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.cost import cost_on_date
from app.domain.inventory.types import InventoryMovementDraft
from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.base import NormalizedWbRow
from app.parsers.wb.semantics import SEMANTICS_VERSION
from app.parsers.wb.semantics_registry import get_semantics_strategy

_OUTBOUND_TYPES = frozenset(
    {
        InventoryOperationType.SALE,
        InventoryOperationType.LOGISTICS_LOSS,
        InventoryOperationType.WAREHOUSE_LOSS,
        InventoryOperationType.DEFECT,
        InventoryOperationType.WRITEOFF,
    }
)
_INBOUND_TYPES = frozenset(
    {
        InventoryOperationType.INBOUND,
        InventoryOperationType.RETURN,
        InventoryOperationType.COMPENSATION,
    }
)


class InventoryMovementBuilder:
    """Extract deterministic inventory movements from normalized WB rows."""

    @staticmethod
    def from_normalized_rows(
        rows: list[NormalizedWbRow],
        *,
        default_date: date,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
    ) -> list[InventoryMovementDraft]:
        costs_by_sku = costs_by_sku or {}
        movements: list[InventoryMovementDraft] = []
        for row in rows:
            draft = InventoryMovementBuilder._movement_for_row(
                row,
                default_date=default_date,
                costs_by_sku=costs_by_sku,
            )
            if draft is not None:
                movements.append(draft)
        return movements

    @staticmethod
    def _movement_for_row(
        row: NormalizedWbRow,
        *,
        default_date: date,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
    ) -> InventoryMovementDraft | None:
        canonical = row.canonical
        strategy = get_semantics_strategy(SEMANTICS_VERSION)
        operation_type = strategy.resolve_operation_type(canonical.get("operation_type"))
        if operation_type is None:
            operation_type = InventoryMovementBuilder._infer_from_amounts(canonical)
        if operation_type is None:
            return None

        quantity = InventoryMovementBuilder._resolve_quantity(canonical, operation_type)
        if quantity == 0:
            return None

        operation_date = row.operation_date or default_date
        sku = row.sku
        unit_cost = None
        if sku:
            unit_cost = cost_on_date(costs_by_sku.get(sku, []), operation_date)

        sale_price = InventoryMovementBuilder._sale_price_per_unit(canonical, quantity)
        total_sale = InventoryMovementBuilder._total_sale_delta(
            operation_type, quantity, sale_price, canonical
        )
        total_cost = InventoryMovementBuilder._total_cost_delta(quantity, unit_cost)

        warehouse = canonical.get("warehouse_name")
        warehouse_name = str(warehouse).strip() if warehouse else None

        return InventoryMovementDraft(
            operation_date=operation_date,
            sku=sku,
            nm_id=row.nm_id,
            warehouse_name=warehouse_name or None,
            operation_type=operation_type,
            quantity_delta=quantity,
            cost_per_unit=unit_cost,
            sale_price_per_unit=sale_price,
            total_cost_delta=total_cost,
            total_sale_delta=total_sale,
            source_row_id=row.source_row_id,
            semantics_version=SEMANTICS_VERSION,
            canonical_payload=dict(canonical),
            raw_payload=dict(row.raw),
        )

    @staticmethod
    def _infer_from_amounts(canonical: dict[str, object]) -> InventoryOperationType | None:
        return_amount = canonical.get("return_amount")
        if isinstance(return_amount, Decimal) and return_amount != Decimal("0"):
            return InventoryOperationType.RETURN
        retail = canonical.get("retail_amount")
        if isinstance(retail, Decimal) and retail != Decimal("0"):
            return InventoryOperationType.SALE
        compensation = canonical.get("compensation")
        if isinstance(compensation, Decimal) and compensation != Decimal("0"):
            return InventoryOperationType.COMPENSATION
        return None

    @staticmethod
    def _resolve_quantity(canonical: dict[str, object], operation_type: InventoryOperationType) -> int:
        raw_qty = canonical.get("quantity")
        if raw_qty is None:
            if operation_type in {
                InventoryOperationType.COMPENSATION,
            }:
                return 0
            if operation_type == InventoryOperationType.SALE and canonical.get("retail_amount"):
                return -1
            if operation_type == InventoryOperationType.RETURN and canonical.get("return_amount"):
                return 1
            return 0

        if isinstance(raw_qty, bool):
            return 0
        if isinstance(raw_qty, int):
            qty = raw_qty
        elif isinstance(raw_qty, (str, float)):
            qty = int(raw_qty)
        else:
            return 0
        if qty == 0:
            return 0

        if operation_type == InventoryOperationType.TRANSFER:
            return qty
        if operation_type == InventoryOperationType.INVENTORY_ADJUSTMENT:
            return qty
        if operation_type in _OUTBOUND_TYPES:
            return -abs(qty)
        if operation_type in _INBOUND_TYPES:
            return abs(qty)
        return int(qty)

    @staticmethod
    def _sale_price_per_unit(canonical: dict[str, object], quantity_delta: int) -> Decimal | None:
        retail = canonical.get("retail_amount")
        if not isinstance(retail, Decimal):
            return None
        units = abs(quantity_delta)
        if units == 0:
            return None
        return (retail / Decimal(units)).quantize(Decimal("0.0001"))

    @staticmethod
    def _total_sale_delta(
        operation_type: InventoryOperationType,
        quantity_delta: int,
        sale_price_per_unit: Decimal | None,
        canonical: dict[str, object],
    ) -> Decimal:
        retail = canonical.get("retail_amount")
        if isinstance(retail, Decimal) and operation_type in {
            InventoryOperationType.SALE,
            InventoryOperationType.RETURN,
        }:
            if operation_type == InventoryOperationType.SALE:
                return abs(retail)
            return abs(retail)
        if sale_price_per_unit is not None:
            return sale_price_per_unit * Decimal(abs(quantity_delta))
        return Decimal("0")

    @staticmethod
    def _total_cost_delta(quantity_delta: int, unit_cost: Decimal | None) -> Decimal:
        if unit_cost is None:
            return Decimal("0")
        return unit_cost * Decimal(quantity_delta)

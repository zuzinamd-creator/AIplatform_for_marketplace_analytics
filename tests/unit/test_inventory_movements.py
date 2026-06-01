from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.cost import cost_on_date
from app.domain.inventory.movements import InventoryMovementBuilder
from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.base import NormalizedWbRow


def _sale_row(*, qty: int = 2, sku: str = "SKU-1") -> NormalizedWbRow:
    return NormalizedWbRow(
        source_row_id="row-0",
        source_row_index=0,
        operation_date=date(2026, 1, 20),
        sku=sku,
        nm_id="123",
        canonical={
            "operation_type": "Продажа",
            "quantity": qty,
            "retail_amount": Decimal("2000"),
            "warehouse_name": "Коледино",
        },
        raw={"Тип операции": "Продажа", "Кол-во": str(qty)},
    )


def test_inventory_movement_extraction_sale_outbound() -> None:
    movements = InventoryMovementBuilder.from_normalized_rows(
        [_sale_row()],
        default_date=date(2026, 1, 1),
    )
    assert len(movements) == 1
    movement = movements[0]
    assert movement.operation_type == InventoryOperationType.SALE
    assert movement.quantity_delta == -2
    assert movement.warehouse_name == "Коледино"
    assert movement.raw_payload["Тип операции"] == "Продажа"
    assert isinstance(movement.total_sale_delta, Decimal)


def test_cost_snapshot_matches_effective_from() -> None:
    history = [
        SkuCostSnapshot(
            sku="SKU-1",
            effective_from=date(2026, 1, 1),
            product_cost=Decimal("50"),
            packaging_cost=Decimal("0"),
            inbound_logistics_cost=Decimal("0"),
            additional_cost=Decimal("0"),
            currency="RUB",
        ),
        SkuCostSnapshot(
            sku="SKU-1",
            effective_from=date(2026, 1, 15),
            product_cost=Decimal("70"),
            packaging_cost=Decimal("0"),
            inbound_logistics_cost=Decimal("0"),
            additional_cost=Decimal("0"),
            currency="RUB",
        ),
    ]
    assert cost_on_date(history, date(2026, 1, 10)) == Decimal("50")
    assert cost_on_date(history, date(2026, 1, 20)) == Decimal("70")


def test_inventory_movement_uses_historical_cost_not_latest_blindly() -> None:
    costs = {
        "SKU-1": [
            SkuCostSnapshot(
                sku="SKU-1",
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("10"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            ),
            SkuCostSnapshot(
                sku="SKU-1",
                effective_from=date(2026, 2, 1),
                product_cost=Decimal("99"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            ),
        ]
    }
    movements = InventoryMovementBuilder.from_normalized_rows(
        [_sale_row(qty=1)],
        default_date=date(2026, 1, 1),
        costs_by_sku=costs,
    )
    movement = movements[0]
    assert movement.cost_per_unit == Decimal("10")
    assert movement.total_cost_delta == Decimal("-10")


def test_inventory_idempotency_natural_key_per_row() -> None:
    movements = InventoryMovementBuilder.from_normalized_rows(
        [_sale_row(), _sale_row()],
        default_date=date(2026, 1, 1),
    )
    keys = {(m.source_row_id, m.operation_type) for m in movements}
    assert keys == {("row-0", InventoryOperationType.SALE)}

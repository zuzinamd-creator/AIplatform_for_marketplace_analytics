from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.reconstruction import InventoryReconstructionService
from app.models.inventory.enums import InventoryOperationType


def _row(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    sku: str = "SKU-1",
) -> InventoryLedgerRow:
    return InventoryLedgerRow(
        operation_date=operation_date,
        sku=sku,
        nm_id=None,
        warehouse_name="WH-1",
        operation_type=operation_type,
        quantity_delta=quantity_delta,
        cost_per_unit=Decimal("10"),
        sale_price_per_unit=Decimal("100") if operation_type == InventoryOperationType.SALE else None,
        semantics_version="1.0",
    )


def test_stock_reconstruction_formula() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 10),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=10,
        ),
        _row(
            operation_date=date(2026, 1, 11),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-3,
        ),
    ]
    snapshots = InventoryReconstructionService.rebuild_from_ledger(movements)
    day1 = next(s for s in snapshots if s.snapshot_date == date(2026, 1, 10))
    day2 = next(s for s in snapshots if s.snapshot_date == date(2026, 1, 11))

    assert day1.opening_stock == 0
    assert day1.inbound_units == 10
    assert day1.expected_closing_stock == 10
    assert day1.actual_stock == 10
    assert day1.discrepancy_units == 0

    assert day2.opening_stock == 10
    assert day2.sold_units == 3
    assert day2.expected_closing_stock == 7
    assert day2.actual_stock == 7


def test_inventory_adjustment_sets_discrepancy() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 12),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=5,
        ),
        _row(
            operation_date=date(2026, 1, 12),
            operation_type=InventoryOperationType.INVENTORY_ADJUSTMENT,
            quantity_delta=2,
        ),
    ]
    snapshots = InventoryReconstructionService.rebuild_from_ledger(movements)
    snap = snapshots[0]
    assert snap.expected_closing_stock == 5
    assert snap.actual_stock == 7
    assert snap.discrepancy_units == 2


def test_rebuild_reproducibility() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 15),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
        ),
        _row(
            operation_date=date(2026, 1, 15),
            operation_type=InventoryOperationType.LOGISTICS_LOSS,
            quantity_delta=-1,
        ),
    ]
    first = InventoryReconstructionService.rebuild_from_ledger(movements)
    second = InventoryReconstructionService.rebuild_from_ledger(movements)
    assert first == second


def test_discrepancy_valuation_uses_historical_cost() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 20),
            operation_type=InventoryOperationType.INVENTORY_ADJUSTMENT,
            quantity_delta=-2,
        ),
    ]
    costs = {
        "SKU-1": [
            SkuCostSnapshot(
                sku="SKU-1",
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("40"),
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
    snapshots, analytics = InventorySnapshotPipeline.rebuild(movements, costs_by_sku=costs)
    snap = snapshots[0]
    assert snap.discrepancy_units == -2
    assert snap.discrepancy_cost == Decimal("-80")
    assert analytics.inventory_losses_units >= 2

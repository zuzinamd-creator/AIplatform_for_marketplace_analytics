"""Inventory stabilization: Decimal safety, incremental rebuild, idempotency."""

from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.reconciliation import InventoryReconciliationService
from app.domain.inventory.reconstruction import InventoryReconstructionService
from app.models.inventory.enums import InventoryOperationType


def _row(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    sku: str = "SKU-1",
    warehouse: str | None = "WH-1",
    sale_price: Decimal | None = None,
) -> InventoryLedgerRow:
    return InventoryLedgerRow(
        operation_date=operation_date,
        sku=sku,
        nm_id=None,
        warehouse_name=warehouse,
        operation_type=operation_type,
        quantity_delta=quantity_delta,
        cost_per_unit=Decimal("10.3333"),
        sale_price_per_unit=sale_price,
        semantics_version="1.0",
    )


def test_decimal_precision_discrepancy_valuation() -> None:
    snap_costs = {
        "SKU-1": [
            SkuCostSnapshot(
                sku="SKU-1",
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("10.3333"),
                packaging_cost=Decimal("0.0001"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            )
        ]
    }
    movements = [
        _row(
            operation_date=date(2026, 1, 5),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            sale_price=Decimal("99.99"),
        ),
        _row(
            operation_date=date(2026, 1, 5),
            operation_type=InventoryOperationType.INVENTORY_ADJUSTMENT,
            quantity_delta=1,
        ),
    ]
    snapshots, _ = InventorySnapshotPipeline.rebuild(movements, costs_by_sku=snap_costs)
    snap = snapshots[0]
    assert isinstance(snap.discrepancy_cost, Decimal)
    assert isinstance(snap.discrepancy_sale_value, Decimal)
    assert snap.discrepancy_cost == Decimal("10.3334")


def test_sale_price_average_decimal_only() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 1),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            sale_price=Decimal("100.01"),
        ),
        _row(
            operation_date=date(2026, 1, 1),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            sale_price=Decimal("200.03"),
        ),
    ]
    index = InventoryReconciliationService.build_sale_price_index(movements)
    avg = index[( "SKU-1", None, "WH-1", date(2026, 1, 1))]
    assert isinstance(avg, Decimal)
    assert avg == Decimal("150.0200")


def test_rebuild_idempotency() -> None:
    movements = [
        _row(
            operation_date=date(2026, 2, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=7,
        ),
    ]
    first, analytics_first = InventorySnapshotPipeline.rebuild(movements, costs_by_sku={})
    second, analytics_second = InventorySnapshotPipeline.rebuild(movements, costs_by_sku={})
    assert first == second
    assert analytics_first == analytics_second


def test_carry_forward_matches_full_history_scan() -> None:
    movements = [
        _row(operation_date=date(2026, 1, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=10),
        _row(operation_date=date(2026, 1, 2), operation_type=InventoryOperationType.SALE, quantity_delta=-3),
        _row(operation_date=date(2026, 1, 3), operation_type=InventoryOperationType.SALE, quantity_delta=-2),
    ]
    full = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=date(2026, 1, 3),
        rebuild_to=date(2026, 1, 3),
    )
    incremental = InventoryReconstructionService.rebuild_from_ledger(
        [movements[2]],
        rebuild_from=date(2026, 1, 3),
        rebuild_to=date(2026, 1, 3),
        initial_opening=7,
    )
    assert full == incremental
    assert full[0].opening_stock == 7


def test_historical_import_rebuilds_future_window() -> None:
    movements = [
        _row(operation_date=date(2026, 1, 10), operation_type=InventoryOperationType.INBOUND, quantity_delta=5),
        _row(operation_date=date(2026, 1, 11), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
        _row(operation_date=date(2026, 1, 12), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    corrected = [
        _row(operation_date=date(2026, 1, 10), operation_type=InventoryOperationType.INBOUND, quantity_delta=12),
        _row(operation_date=date(2026, 1, 11), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
        _row(operation_date=date(2026, 1, 12), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    window_from = date(2026, 1, 10)
    window_to = date(2026, 1, 12)
    before = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=window_from,
        rebuild_to=window_to,
    )
    after = InventoryReconstructionService.rebuild_from_ledger(
        corrected,
        rebuild_from=window_from,
        rebuild_to=window_to,
    )
    day11_before = next(s for s in before if s.snapshot_date == date(2026, 1, 11))
    day11_after = next(s for s in after if s.snapshot_date == date(2026, 1, 11))
    assert day11_before.opening_stock == 5
    assert day11_after.opening_stock == 12


def test_stale_snapshot_window_recompute_differs_from_unrelated_history() -> None:
    """Window rebuild must not emit snapshots outside [rebuild_from, rebuild_to]."""
    movements = [
        _row(operation_date=date(2026, 1, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=1),
        _row(operation_date=date(2026, 1, 15), operation_type=InventoryOperationType.INBOUND, quantity_delta=50),
        _row(operation_date=date(2026, 1, 16), operation_type=InventoryOperationType.SALE, quantity_delta=-5),
    ]
    windowed = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=date(2026, 1, 15),
        rebuild_to=date(2026, 1, 16),
        initial_opening=100,
    )
    dates = {s.snapshot_date for s in windowed}
    assert dates == {date(2026, 1, 15), date(2026, 1, 16)}
    day15 = next(s for s in windowed if s.snapshot_date == date(2026, 1, 15))
    assert day15.opening_stock == 100

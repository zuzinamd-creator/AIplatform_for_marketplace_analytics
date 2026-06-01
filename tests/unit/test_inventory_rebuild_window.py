"""Rebuild window propagation: future snapshots must be included in rebuild horizon."""

from datetime import date
from decimal import Decimal

from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.rebuild_window import compute_rebuild_window
from app.domain.inventory.reconstruction import InventoryReconstructionService
from app.models.inventory.enums import InventoryOperationType


def _row(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    sku: str = "SKU-1",
    warehouse: str | None = "WH-A",
) -> InventoryLedgerRow:
    return InventoryLedgerRow(
        operation_date=operation_date,
        sku=sku,
        nm_id=None,
        warehouse_name=warehouse,
        operation_type=operation_type,
        quantity_delta=quantity_delta,
        cost_per_unit=Decimal("1"),
        sale_price_per_unit=None,
        semantics_version="1.0",
    )


def test_rebuild_to_extends_to_latest_snapshot_not_only_ledger() -> None:
    """Stale future snapshots must be cleared: horizon uses max(snapshot, ledger)."""
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 1, 10),
        latest_snapshot_date=date(2026, 1, 25),
        latest_ledger_date=date(2026, 1, 15),
    )
    assert window.rebuild_from == date(2026, 1, 10)
    assert window.rebuild_to == date(2026, 1, 25)


def test_historical_report_import_rebuilds_future_snapshots() -> None:
    """Late import on T=10 must shift opening on T=11 and T=12."""
    original = [
        _row(operation_date=date(2026, 1, 10), operation_type=InventoryOperationType.INBOUND, quantity_delta=10),
        _row(operation_date=date(2026, 1, 11), operation_type=InventoryOperationType.SALE, quantity_delta=-2),
        _row(operation_date=date(2026, 1, 12), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    corrected = [
        _row(operation_date=date(2026, 1, 10), operation_type=InventoryOperationType.INBOUND, quantity_delta=20),
        _row(operation_date=date(2026, 1, 11), operation_type=InventoryOperationType.SALE, quantity_delta=-2),
        _row(operation_date=date(2026, 1, 12), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 1, 10),
        latest_snapshot_date=date(2026, 1, 12),
        latest_ledger_date=date(2026, 1, 12),
    )
    before = InventoryReconstructionService.rebuild_from_ledger(
        original,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    after = InventoryReconstructionService.rebuild_from_ledger(
        corrected,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    assert before != after
    day11_after = next(s for s in after if s.snapshot_date == date(2026, 1, 11))
    assert day11_after.opening_stock == 20


def test_future_report_import_within_window() -> None:
    movements = [
        _row(operation_date=date(2026, 2, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=5),
        _row(operation_date=date(2026, 2, 5), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
        _row(operation_date=date(2026, 2, 20), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 2, 5),
        latest_snapshot_date=date(2026, 2, 28),
        latest_ledger_date=date(2026, 2, 20),
    )
    snapshots = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    dates = {s.snapshot_date for s in snapshots}
    assert date(2026, 2, 5) in dates
    assert date(2026, 2, 20) in dates
    assert window.rebuild_to == date(2026, 2, 28)


def test_repeated_import_produces_identical_snapshots() -> None:
    movements = [
        _row(operation_date=date(2026, 3, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=3),
        _row(operation_date=date(2026, 3, 2), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 3, 1),
        latest_snapshot_date=date(2026, 3, 10),
        latest_ledger_date=date(2026, 3, 2),
    )
    first = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    second = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    assert first == second


def test_sparse_dates_carry_opening_across_gaps() -> None:
    movements = [
        _row(operation_date=date(2026, 4, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=10),
        _row(operation_date=date(2026, 4, 10), operation_type=InventoryOperationType.SALE, quantity_delta=-4),
    ]
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 4, 1),
        latest_snapshot_date=date(2026, 4, 30),
        latest_ledger_date=date(2026, 4, 10),
    )
    snapshots = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    day10 = next(s for s in snapshots if s.snapshot_date == date(2026, 4, 10))
    assert day10.opening_stock == 10
    assert day10.actual_stock == 6


def test_multiple_skus_isolated() -> None:
    movements = [
        _row(
            operation_date=date(2026, 5, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=10,
            sku="SKU-A",
        ),
        _row(
            operation_date=date(2026, 5, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=20,
            sku="SKU-B",
        ),
        _row(
            operation_date=date(2026, 5, 2),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            sku="SKU-A",
        ),
    ]
    snapshots = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=date(2026, 5, 1),
        rebuild_to=date(2026, 5, 2),
    )
    sku_a = next(s for s in snapshots if s.sku == "SKU-A" and s.snapshot_date == date(2026, 5, 2))
    sku_b = next(s for s in snapshots if s.sku == "SKU-B")
    assert sku_a.opening_stock == 10
    assert sku_b.actual_stock == 20


def test_multiple_warehouses_isolated() -> None:
    movements = [
        _row(
            operation_date=date(2026, 6, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=5,
            warehouse="WH-1",
        ),
        _row(
            operation_date=date(2026, 6, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=8,
            warehouse="WH-2",
        ),
    ]
    snapshots = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=date(2026, 6, 1),
        rebuild_to=date(2026, 6, 1),
    )
    wh1 = next(s for s in snapshots if s.warehouse_name == "WH-1")
    wh2 = next(s for s in snapshots if s.warehouse_name == "WH-2")
    assert wh1.actual_stock == 5
    assert wh2.actual_stock == 8


def test_no_stale_closing_after_mid_history_correction() -> None:
    """Correction on day 2 must update day 3 closing; day 3 must not keep pre-correction balance."""
    v1 = [
        _row(operation_date=date(2026, 7, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=10),
        _row(operation_date=date(2026, 7, 2), operation_type=InventoryOperationType.SALE, quantity_delta=-2),
        _row(operation_date=date(2026, 7, 3), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    v2 = [
        _row(operation_date=date(2026, 7, 1), operation_type=InventoryOperationType.INBOUND, quantity_delta=10),
        _row(operation_date=date(2026, 7, 2), operation_type=InventoryOperationType.INBOUND, quantity_delta=5),
        _row(operation_date=date(2026, 7, 3), operation_type=InventoryOperationType.SALE, quantity_delta=-1),
    ]
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 7, 2),
        latest_snapshot_date=date(2026, 7, 3),
        latest_ledger_date=date(2026, 7, 3),
    )
    stale = InventoryReconstructionService.rebuild_from_ledger(
        v1,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    fresh = InventoryReconstructionService.rebuild_from_ledger(
        v2,
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
    )
    stale_day3 = next(s for s in stale if s.snapshot_date == date(2026, 7, 3))
    fresh_day3 = next(s for s in fresh if s.snapshot_date == date(2026, 7, 3))
    assert stale_day3.opening_stock == 8
    assert fresh_day3.opening_stock == 15
    assert fresh_day3.actual_stock == 14

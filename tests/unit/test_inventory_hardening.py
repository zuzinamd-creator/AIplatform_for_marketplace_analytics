from datetime import date
from decimal import Decimal

import pytest
from app.domain.inventory.errors import OpeningBalanceIntegrityError
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.opening_balance import validate_opening_balance_integrity
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.rebuild_window import compute_rebuild_window
from app.domain.inventory.reconstruction import InventoryReconstructionService
from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.semantics_registry import (
    SEMANTICS_REGISTRY,
    DayMovementBuckets,
    OperationSemanticsStrategyV1,
    get_semantics_strategy,
)


def _row(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    semantics_version: str = "1.0",
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
        sale_price_per_unit=None,
        semantics_version=semantics_version,
    )


def test_rebuild_window_propagates_to_latest_snapshot() -> None:
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 1, 10),
        latest_snapshot_date=date(2026, 1, 20),
        latest_ledger_date=date(2026, 1, 18),
    )
    assert window.rebuild_from == date(2026, 1, 10)
    assert window.rebuild_to == date(2026, 1, 20)


def test_historical_rebuild_propagation_recomputes_future_snapshots() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 10),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=10,
        ),
        _row(
            operation_date=date(2026, 1, 11),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-2,
        ),
        _row(
            operation_date=date(2026, 1, 12),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
        ),
    ]
    full = InventoryReconstructionService.rebuild_from_ledger(movements)
    windowed = InventoryReconstructionService.rebuild_from_ledger(
        movements,
        rebuild_from=date(2026, 1, 10),
        rebuild_to=date(2026, 1, 12),
    )
    assert len(windowed) == 3
    assert windowed == full

    late_import = [
        _row(
            operation_date=date(2026, 1, 10),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=15,
        ),
        _row(
            operation_date=date(2026, 1, 11),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-2,
        ),
        _row(
            operation_date=date(2026, 1, 12),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
        ),
    ]
    rebuilt = InventoryReconstructionService.rebuild_from_ledger(
        late_import,
        rebuild_from=date(2026, 1, 10),
        rebuild_to=date(2026, 1, 12),
    )
    day11 = next(s for s in rebuilt if s.snapshot_date == date(2026, 1, 11))
    assert day11.opening_stock == 15
    day12 = next(s for s in rebuilt if s.snapshot_date == date(2026, 1, 12))
    assert day12.opening_stock == 13


def test_version_aware_reconstruction_uses_row_semantics() -> None:
    class OperationSemanticsStrategyV2(OperationSemanticsStrategyV1):
        version = "2.0"

        def classify_movement(self, row: InventoryLedgerRow) -> DayMovementBuckets:
            if row.operation_type == InventoryOperationType.COMPENSATION:
                return DayMovementBuckets(inbound=abs(row.quantity_delta) * 2)
            return super().classify_movement(row)

    from app.domain.semantics.governance_policy import (
        SemanticsLifecycleRecord,
        SemanticsLifecycleStatus,
        set_lifecycle_cache,
    )

    SEMANTICS_REGISTRY["2.0"] = OperationSemanticsStrategyV2()
    set_lifecycle_cache(
        {
            "2.0": SemanticsLifecycleRecord(
                version="2.0",
                status=SemanticsLifecycleStatus.ACTIVE,
                supported_for_rebuild=True,
                supported_for_ingest=True,
            ),
        }
    )

    try:
        movements = [
            _row(
                operation_date=date(2026, 2, 1),
                operation_type=InventoryOperationType.COMPENSATION,
                quantity_delta=3,
                semantics_version="1.0",
            ),
            _row(
                operation_date=date(2026, 2, 1),
                operation_type=InventoryOperationType.COMPENSATION,
                quantity_delta=3,
                semantics_version="2.0",
                sku="SKU-2",
            ),
        ]
        snapshots = InventoryReconstructionService.rebuild_from_ledger(movements)
        v1 = next(s for s in snapshots if s.sku == "SKU-1")
        v2 = next(s for s in snapshots if s.sku == "SKU-2")
        assert v1.inbound_units == 3
        assert v2.inbound_units == 6
    finally:
        del SEMANTICS_REGISTRY["2.0"]


def test_opening_balance_overlap_raises() -> None:
    with pytest.raises(OpeningBalanceIntegrityError):
        validate_opening_balance_integrity(
            opening_date=date(2026, 1, 10),
            sku="SKU-1",
            warehouse_name="WH-1",
            first_ledger_operation_date=date(2026, 1, 5),
        )


def test_snapshot_rebuild_determinism() -> None:
    movements = [
        _row(
            operation_date=date(2026, 3, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=4,
        ),
    ]
    first, _ = InventorySnapshotPipeline.rebuild(movements, costs_by_sku={})
    second, _ = InventorySnapshotPipeline.rebuild(movements, costs_by_sku={})
    assert first == second


def test_unsupported_semantics_version_raises() -> None:
    from app.domain.inventory.errors import UnsupportedSemanticsVersionError

    with pytest.raises(UnsupportedSemanticsVersionError):
        get_semantics_strategy("99.0")

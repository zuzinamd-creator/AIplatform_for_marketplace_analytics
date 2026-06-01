from datetime import date
from decimal import Decimal

import pytest
from app.domain.inventory.errors import UnsupportedSemanticsVersionError
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.reconstruction import InventoryReconstructionService
from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.semantics_registry import (
    SEMANTICS_REGISTRY,
    DayMovementBuckets,
    OperationSemanticsStrategyV1,
    build_strategy_cache,
    collect_semantics_versions,
)


def _row(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    semantics_version: str,
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


def test_v1_reconstruction() -> None:
    movements = [
        _row(
            operation_date=date(2026, 1, 10),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=5,
            semantics_version="1.0",
        ),
    ]
    snapshots = InventoryReconstructionService.rebuild_from_ledger(movements)
    assert snapshots[0].inbound_units == 5


def test_mixed_version_reconstruction() -> None:
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
                sku="SKU-V1",
            ),
            _row(
                operation_date=date(2026, 2, 1),
                operation_type=InventoryOperationType.COMPENSATION,
                quantity_delta=3,
                semantics_version="2.0",
                sku="SKU-V2",
            ),
        ]
        cache = build_strategy_cache(collect_semantics_versions(movements))
        assert "1.0" in cache
        assert "2.0" in cache

        snapshots = InventoryReconstructionService.rebuild_from_ledger(movements)
        v1 = next(s for s in snapshots if s.sku == "SKU-V1")
        v2 = next(s for s in snapshots if s.sku == "SKU-V2")
        assert v1.inbound_units == 3
        assert v2.inbound_units == 6
    finally:
        SEMANTICS_REGISTRY.pop("2.0", None)


def test_missing_strategy_raises() -> None:
    with pytest.raises(UnsupportedSemanticsVersionError):
        build_strategy_cache({"99.0"})


def test_missing_row_semantics_version_raises() -> None:
    row = InventoryLedgerRow(
        operation_date=date(2026, 3, 1),
        sku="SKU-1",
        nm_id=None,
        warehouse_name="WH-1",
        operation_type=InventoryOperationType.SALE,
        quantity_delta=-1,
        cost_per_unit=None,
        sale_price_per_unit=None,
        semantics_version="",
    )
    with pytest.raises(UnsupportedSemanticsVersionError):
        InventoryReconstructionService.rebuild_from_ledger([row])


def test_deterministic_rebuild_after_semantics_upgrade_registered() -> None:
    """Rows keep historical version; new registry entry does not alter v1 rows."""
    class OperationSemanticsStrategyV2(OperationSemanticsStrategyV1):
        version = "2.0"

        def classify_movement(self, row: InventoryLedgerRow) -> DayMovementBuckets:
            if row.operation_type == InventoryOperationType.SALE:
                return DayMovementBuckets(sold=abs(row.quantity_delta) * 10)
            return super().classify_movement(row)

    movements = [
        _row(
            operation_date=date(2026, 4, 1),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            semantics_version="1.0",
        ),
    ]
    before_upgrade, _ = InventorySnapshotPipeline.rebuild(movements, costs_by_sku={})

    SEMANTICS_REGISTRY["2.0"] = OperationSemanticsStrategyV2()
    try:
        after_upgrade, _ = InventorySnapshotPipeline.rebuild(movements, costs_by_sku={})
    finally:
        SEMANTICS_REGISTRY.pop("2.0", None)

    assert before_upgrade == after_upgrade
    assert before_upgrade[0].sold_units == 1


def test_strategy_cache_built_once_not_per_row() -> None:
    movements = [
        _row(
            operation_date=date(2026, 5, i),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=1,
            semantics_version="1.0",
        )
        for i in range(1, 6)
    ]
    versions = collect_semantics_versions(movements)
    cache = build_strategy_cache(versions)
    assert len(cache) == 1
    assert cache["1.0"].version == "1.0"

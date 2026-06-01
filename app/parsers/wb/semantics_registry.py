"""Versioned operation semantics for historical inventory determinism."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.inventory.errors import UnsupportedSemanticsVersionError
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.semantics_version import require_semantics_version
from app.domain.semantics.governance_policy import assert_ingest_allowed, assert_rebuild_allowed
from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb import operation_semantics as semantics_v1
from app.parsers.wb.semantics import SEMANTICS_VERSION

_LOSS_TYPES_V1 = frozenset(
    {
        InventoryOperationType.LOGISTICS_LOSS,
        InventoryOperationType.WAREHOUSE_LOSS,
        InventoryOperationType.DEFECT,
    }
)


@dataclass(frozen=True)
class DayMovementBuckets:
    inbound: int = 0
    sold: int = 0
    returned: int = 0
    lost: int = 0
    writeoff: int = 0
    adjustment_delta: int = 0


class OperationSemanticsStrategyV1:
    """Semantics frozen at version 1.0 — uses persisted operation_type from ingest."""

    version = "1.0"

    def resolve_operation_type(self, operation_label: object) -> InventoryOperationType | None:
        return semantics_v1.resolve_inventory_operation_type(operation_label)

    def classify_movement(self, row: InventoryLedgerRow) -> DayMovementBuckets:
        qty = row.quantity_delta
        op = row.operation_type
        buckets = DayMovementBuckets()

        if op == InventoryOperationType.INVENTORY_ADJUSTMENT:
            return DayMovementBuckets(adjustment_delta=qty)

        if op in {InventoryOperationType.INBOUND, InventoryOperationType.COMPENSATION}:
            return DayMovementBuckets(inbound=abs(qty) if qty != 0 else 0)

        if op == InventoryOperationType.SALE:
            return DayMovementBuckets(sold=abs(qty))

        if op == InventoryOperationType.RETURN:
            return DayMovementBuckets(returned=abs(qty))

        if op in _LOSS_TYPES_V1:
            return DayMovementBuckets(lost=abs(qty))

        if op == InventoryOperationType.WRITEOFF:
            return DayMovementBuckets(writeoff=abs(qty))

        if op == InventoryOperationType.TRANSFER:
            if qty > 0:
                return DayMovementBuckets(inbound=qty)
            if qty < 0:
                return DayMovementBuckets(sold=abs(qty))

        return buckets


SEMANTICS_REGISTRY: dict[str, OperationSemanticsStrategyV1] = {
    "1.0": OperationSemanticsStrategyV1(),
}


def build_strategy_cache(versions: set[str]) -> dict[str, OperationSemanticsStrategyV1]:
    """Resolve semantics strategies once before hot-loop classification."""
    cache: dict[str, OperationSemanticsStrategyV1] = {}
    for version in versions:
        normalized = require_semantics_version(version)
        assert_rebuild_allowed(normalized)
        strategy = SEMANTICS_REGISTRY.get(normalized)
        if strategy is None:
            raise UnsupportedSemanticsVersionError(normalized)
        cache[normalized] = strategy
    return cache


def collect_semantics_versions(movements: list[InventoryLedgerRow]) -> set[str]:
    versions: set[str] = set()
    for row in movements:
        versions.add(require_semantics_version(row.semantics_version))
    return versions


def get_semantics_strategy(version: str) -> OperationSemanticsStrategyV1:
    normalized = require_semantics_version(version)
    assert_ingest_allowed(normalized)
    strategy = SEMANTICS_REGISTRY.get(normalized)
    if strategy is None:
        raise UnsupportedSemanticsVersionError(normalized)
    return strategy


def default_semantics_version() -> str:
    return SEMANTICS_VERSION

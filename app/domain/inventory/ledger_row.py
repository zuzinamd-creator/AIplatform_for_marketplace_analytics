from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.inventory.semantics_version import require_semantics_version
from app.domain.inventory.types import InventoryMovementDraft
from app.models.inventory.enums import InventoryOperationType
from app.models.inventory.ledger import InventoryLedgerEntry


@dataclass(frozen=True)
class InventoryLedgerRow:
    """Normalized inventory movement for reconstruction (DB or in-memory)."""

    operation_date: date
    sku: str | None
    nm_id: str | None
    warehouse_name: str | None
    operation_type: InventoryOperationType
    quantity_delta: int
    cost_per_unit: Decimal | None
    sale_price_per_unit: Decimal | None
    semantics_version: str
    source_row_id: str = ""

    @staticmethod
    def from_draft(draft: InventoryMovementDraft) -> InventoryLedgerRow:
        return InventoryLedgerRow(
            operation_date=draft.operation_date,
            sku=draft.sku,
            nm_id=draft.nm_id,
            warehouse_name=draft.warehouse_name,
            operation_type=draft.operation_type,
            quantity_delta=draft.quantity_delta,
            cost_per_unit=draft.cost_per_unit,
            sale_price_per_unit=draft.sale_price_per_unit,
            semantics_version=require_semantics_version(draft.semantics_version),
            source_row_id=draft.source_row_id,
        )

    @staticmethod
    def from_entry(entry: InventoryLedgerEntry) -> InventoryLedgerRow:
        return InventoryLedgerRow(
            operation_date=entry.operation_date,
            sku=entry.sku,
            nm_id=entry.nm_id,
            warehouse_name=entry.warehouse_name,
            operation_type=entry.operation_type,
            quantity_delta=entry.quantity_delta,
            cost_per_unit=entry.cost_per_unit,
            sale_price_per_unit=entry.sale_price_per_unit,
            semantics_version=require_semantics_version(entry.semantics_version),
            source_row_id=entry.source_row_id,
        )

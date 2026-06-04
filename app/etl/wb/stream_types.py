from __future__ import annotations

from dataclasses import dataclass

from app.domain.finance.types import LedgerEntryDraft
from app.domain.inventory.types import InventoryMovementDraft
from app.domain.reconciliation.calculator import ReconciliationResult
from app.parsers.wb.base import NormalizedWbRow


@dataclass(frozen=True)
class WbProcessChunk:
    """One CPU chunk ready for phase-1 persist (not retained after write)."""

    parser_name: str
    parser_version: str
    normalized_rows: list[NormalizedWbRow]
    ledger_entries: list[LedgerEntryDraft]
    inventory_movements: list[InventoryMovementDraft]
    reconciliation: ReconciliationResult

from datetime import date
from decimal import Decimal

from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.snapshot_fingerprint import (
    fingerprint_from_draft,
    ledger_day_fingerprint,
    snapshot_state_fingerprint,
)
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.models.inventory.enums import InventoryOperationType


def _row(*, source_row_id: str, qty: int) -> InventoryLedgerRow:
    return InventoryLedgerRow(
        operation_date=date(2026, 1, 10),
        sku="SKU-1",
        nm_id=None,
        warehouse_name="WH",
        operation_type=InventoryOperationType.INBOUND,
        quantity_delta=qty,
        cost_per_unit=Decimal("10"),
        sale_price_per_unit=None,
        semantics_version="1.0",
        source_row_id=source_row_id,
    )


def test_snapshot_fingerprint_ignores_timestamps_and_is_stable() -> None:
    first = snapshot_state_fingerprint(
        opening_stock=5,
        inbound_units=5,
        sold_units=0,
        returned_units=0,
        lost_units=0,
        writeoff_units=0,
        actual_stock=5,
        discrepancy_units=0,
        semantics_version="1.0",
    )
    second = snapshot_state_fingerprint(
        opening_stock=5,
        inbound_units=5,
        sold_units=0,
        returned_units=0,
        lost_units=0,
        writeoff_units=0,
        actual_stock=5,
        discrepancy_units=0,
        semantics_version="1.0",
    )
    assert first == second


def test_ledger_day_fingerprint_order_is_deterministic() -> None:
    rows_a = [_row(source_row_id="b", qty=2), _row(source_row_id="a", qty=1)]
    rows_b = [_row(source_row_id="a", qty=1), _row(source_row_id="b", qty=2)]
    assert ledger_day_fingerprint(rows_a) == ledger_day_fingerprint(rows_b)


def test_fingerprint_from_draft_matches_state_helper() -> None:
    draft = WarehouseStockSnapshotDraft(
        snapshot_date=date(2026, 1, 11),
        sku="SKU-1",
        nm_id=None,
        warehouse_name="WH",
        opening_stock=5,
        inbound_units=0,
        sold_units=2,
        returned_units=0,
        lost_units=0,
        writeoff_units=0,
        expected_closing_stock=3,
        actual_stock=3,
        discrepancy_units=0,
        discrepancy_cost=Decimal("0"),
        discrepancy_sale_value=Decimal("0"),
        semantics_version="1.0",
    )
    assert fingerprint_from_draft(draft) == snapshot_state_fingerprint(
        opening_stock=5,
        inbound_units=0,
        sold_units=2,
        returned_units=0,
        lost_units=0,
        writeoff_units=0,
        actual_stock=3,
        discrepancy_units=0,
        semantics_version="1.0",
    )

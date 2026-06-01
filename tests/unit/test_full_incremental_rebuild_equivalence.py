"""Incremental (carry-forward) vs full ledger replay must match when snapshots are clean."""

from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.snapshot_fingerprint import fingerprint_from_draft
from app.models.inventory.enums import InventoryOperationType


def _row(
    *,
    op_date: date,
    op_type: InventoryOperationType,
    qty: int,
    source_row_id: str,
) -> InventoryLedgerRow:
    return InventoryLedgerRow(
        operation_date=op_date,
        sku="SKU-EQ",
        nm_id=None,
        warehouse_name="WH-1",
        operation_type=op_type,
        quantity_delta=qty,
        cost_per_unit=Decimal("10"),
        sale_price_per_unit=Decimal("20") if op_type == InventoryOperationType.SALE else None,
        semantics_version="1.0",
        source_row_id=source_row_id,
    )


def test_full_replay_matches_incremental_with_clean_carry_forward() -> None:
    movements = [
        _row(
            op_date=date(2026, 1, 10),
            op_type=InventoryOperationType.INBOUND,
            qty=5,
            source_row_id="r1",
        ),
        _row(
            op_date=date(2026, 1, 11),
            op_type=InventoryOperationType.SALE,
            qty=-2,
            source_row_id="r2",
        ),
    ]
    costs: dict[str, list[SkuCostSnapshot]] = {
        "SKU-EQ": [
            SkuCostSnapshot(
                sku="SKU-EQ",
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("10"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            )
        ]
    }

    full_snaps, _ = InventorySnapshotPipeline.rebuild(
        movements,
        costs_by_sku=costs,
        rebuild_from=date(2026, 1, 10),
        rebuild_to=date(2026, 1, 11),
        initial_opening=None,
    )

    incremental_snaps, _ = InventorySnapshotPipeline.rebuild(
        [movements[1]],
        costs_by_sku=costs,
        rebuild_from=date(2026, 1, 11),
        rebuild_to=date(2026, 1, 11),
        initial_opening=5,
    )

    full_by_date = {snap.snapshot_date: snap for snap in full_snaps}
    inc_by_date = {snap.snapshot_date: snap for snap in incremental_snaps}

    assert fingerprint_from_draft(full_by_date[date(2026, 1, 11)]) == fingerprint_from_draft(
        inc_by_date[date(2026, 1, 11)]
    )

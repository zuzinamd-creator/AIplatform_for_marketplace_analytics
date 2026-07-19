"""Phase 9.17-E — Safe Incremental Stream v1 (Variant B) equivalence tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.rebuild_window import compute_rebuild_window
from app.domain.inventory.snapshot_fingerprint import fingerprint_from_draft
from app.etl.wb.inventory_ledger_streaming import row_kept_by_variant_b
from app.models.inventory.enums import InventoryOperationType


def _row(
    *,
    operation_date: date,
    operation_type: InventoryOperationType,
    quantity_delta: int,
    sku: str = "SKU-1",
    warehouse: str | None = "WH-1",
    nm_id: str | None = None,
    source_row_id: str = "r1",
) -> InventoryLedgerRow:
    return InventoryLedgerRow(
        operation_date=operation_date,
        sku=sku,
        nm_id=nm_id,
        warehouse_name=warehouse,
        operation_type=operation_type,
        quantity_delta=quantity_delta,
        cost_per_unit=Decimal("10"),
        sale_price_per_unit=Decimal("20") if operation_type == InventoryOperationType.SALE else None,
        semantics_version="1.0",
        source_row_id=source_row_id,
    )


def _costs(sku: str = "SKU-1") -> dict[str, list[SkuCostSnapshot]]:
    return {
        sku: [
            SkuCostSnapshot(
                sku=sku,
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("10"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            )
        ]
    }


def _key(row: InventoryLedgerRow) -> tuple[str | None, str | None, str | None]:
    return (row.sku, row.nm_id, row.warehouse_name)


def test_variant_b_predicate_skips_prewindow_only_for_carry_keys() -> None:
    rebuild_from = date(2026, 7, 6)
    carry = {("SKU-A", None, "WH-1")}
    assert row_kept_by_variant_b(
        key=("SKU-A", None, "WH-1"),
        operation_date=date(2026, 7, 1),
        rebuild_from=rebuild_from,
        carry_forward_keys=carry,
    ) is False
    assert row_kept_by_variant_b(
        key=("SKU-A", None, "WH-1"),
        operation_date=date(2026, 7, 6),
        rebuild_from=rebuild_from,
        carry_forward_keys=carry,
    ) is True
    # Hole key — keep full history
    assert row_kept_by_variant_b(
        key=("SKU-HOLE", None, "WH-1"),
        operation_date=date(2026, 3, 1),
        rebuild_from=rebuild_from,
        carry_forward_keys=carry,
    ) is True


def test_carry_forward_scenario_fingerprints_identical() -> None:
    """Keys with carry-forward: window-only movements + opening ≡ full replay."""
    movements = [
        _row(
            operation_date=date(2026, 1, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=20,
            source_row_id="a",
        ),
        _row(
            operation_date=date(2026, 1, 2),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-5,
            source_row_id="b",
        ),
        _row(
            operation_date=date(2026, 1, 3),
            operation_type=InventoryOperationType.RETURN,
            quantity_delta=2,
            source_row_id="c",
        ),
        _row(
            operation_date=date(2026, 1, 4),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            source_row_id="d",
        ),
    ]
    rebuild_from = date(2026, 1, 3)
    rebuild_to = date(2026, 1, 4)
    costs = _costs()

    full, _ = InventorySnapshotPipeline.rebuild(
        movements,
        costs_by_sku=costs,
        rebuild_from=rebuild_from,
        rebuild_to=rebuild_to,
        initial_opening=None,
    )
    # Opening after day 2: 20 - 5 = 15
    filtered = [
        m
        for m in movements
        if row_kept_by_variant_b(
            key=_key(m),
            operation_date=m.operation_date,
            rebuild_from=rebuild_from,
            carry_forward_keys={_key(movements[0])},
        )
    ]
    incremental, _ = InventorySnapshotPipeline.rebuild(
        filtered,
        costs_by_sku=costs,
        rebuild_from=rebuild_from,
        rebuild_to=rebuild_to,
        initial_opening=15,
    )
    assert {s.snapshot_date: fingerprint_from_draft(s) for s in full} == {
        s.snapshot_date: fingerprint_from_draft(s) for s in incremental
    }
    assert full[-1].actual_stock == incremental[-1].actual_stock


def test_hole_key_no_snapshot_keeps_full_history() -> None:
    """Key without carry-forward must replay pre-window history (Variant B)."""
    hole = [
        _row(
            operation_date=date(2026, 1, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=50,
            sku="HOLE",
            source_row_id="h1",
        ),
        _row(
            operation_date=date(2026, 1, 10),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-8,
            sku="HOLE",
            source_row_id="h2",
        ),
    ]
    other_carry_key = ("OTHER", None, "WH-1")
    rebuild_from = date(2026, 1, 10)
    kept = [
        m
        for m in hole
        if row_kept_by_variant_b(
            key=_key(m),
            operation_date=m.operation_date,
            rebuild_from=rebuild_from,
            carry_forward_keys={other_carry_key},
        )
    ]
    assert len(kept) == 2  # full history retained for hole key

    full, _ = InventorySnapshotPipeline.rebuild(
        hole,
        costs_by_sku=_costs("HOLE"),
        rebuild_from=rebuild_from,
        rebuild_to=date(2026, 1, 10),
        initial_opening=None,
    )
    via_filter, _ = InventorySnapshotPipeline.rebuild(
        kept,
        costs_by_sku=_costs("HOLE"),
        rebuild_from=rebuild_from,
        rebuild_to=date(2026, 1, 10),
        initial_opening=None,
    )
    assert fingerprint_from_draft(full[0]) == fingerprint_from_draft(via_filter[0])
    assert full[0].opening_stock == 50
    assert full[0].actual_stock == 42


def test_no_snapshot_scenario_opening_from_ledger() -> None:
    """Empty carry set → predicate keeps all rows; reconstruction uses ledger only."""
    movements = [
        _row(
            operation_date=date(2026, 2, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=10,
            source_row_id="n1",
        ),
        _row(
            operation_date=date(2026, 2, 5),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-3,
            source_row_id="n2",
        ),
    ]
    rebuild_from = date(2026, 2, 5)
    kept = [
        m
        for m in movements
        if row_kept_by_variant_b(
            key=_key(m),
            operation_date=m.operation_date,
            rebuild_from=rebuild_from,
            carry_forward_keys=set(),
        )
    ]
    assert kept == movements
    snaps, _ = InventorySnapshotPipeline.rebuild(
        kept,
        costs_by_sku=_costs(),
        rebuild_from=rebuild_from,
        rebuild_to=date(2026, 2, 5),
        initial_opening=None,
    )
    assert snaps[0].opening_stock == 10
    assert snaps[0].actual_stock == 7


def test_late_movement_expands_rebuild_from() -> None:
    """Late-dated movement in a new report must expand the window (earliest_affected)."""
    window = compute_rebuild_window(
        earliest_affected_date=date(2026, 5, 1),  # late op dated May 1
        latest_snapshot_date=date(2026, 7, 12),
        latest_ledger_date=date(2026, 7, 12),
    )
    assert window.rebuild_from == date(2026, 5, 1)
    assert window.rebuild_to == date(2026, 7, 12)

    movements = [
        _row(
            operation_date=date(2026, 4, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=100,
            source_row_id="old",
        ),
        _row(
            operation_date=date(2026, 5, 1),
            operation_type=InventoryOperationType.INVENTORY_ADJUSTMENT,
            quantity_delta=-5,
            source_row_id="late",
        ),
        _row(
            operation_date=date(2026, 7, 10),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            source_row_id="new",
        ),
    ]
    carry = {_key(movements[0])}
    # With carry opening=100 as of before May 1, Variant B keeps >= May 1
    kept = [
        m
        for m in movements
        if row_kept_by_variant_b(
            key=_key(m),
            operation_date=m.operation_date,
            rebuild_from=window.rebuild_from,
            carry_forward_keys=carry,
        )
    ]
    assert [m.source_row_id for m in kept] == ["late", "new"]
    snaps, _ = InventorySnapshotPipeline.rebuild(
        kept,
        costs_by_sku=_costs(),
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
        initial_opening=100,
    )
    by_date = {s.snapshot_date: s for s in snaps}
    assert by_date[date(2026, 5, 1)].opening_stock == 100
    assert by_date[date(2026, 5, 1)].actual_stock == 95
    full, _ = InventorySnapshotPipeline.rebuild(
        movements,
        costs_by_sku=_costs(),
        rebuild_from=window.rebuild_from,
        rebuild_to=window.rebuild_to,
        initial_opening=None,
    )
    full_by = {s.snapshot_date: s for s in full}
    assert fingerprint_from_draft(full_by[date(2026, 5, 1)]) == fingerprint_from_draft(
        by_date[date(2026, 5, 1)]
    )
    assert fingerprint_from_draft(full_by[date(2026, 7, 10)]) == fingerprint_from_draft(
        by_date[date(2026, 7, 10)]
    )


def test_old_vs_new_filter_same_row_set() -> None:
    """Legacy Python skip ≡ Variant B predicate on mixed carry/hole keys."""
    rows = [
        _row(
            operation_date=date(2026, 6, 1),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=1,
            sku="A",
            source_row_id="1",
        ),
        _row(
            operation_date=date(2026, 7, 10),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-1,
            sku="A",
            source_row_id="2",
        ),
        _row(
            operation_date=date(2026, 6, 15),
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=9,
            sku="HOLE",
            source_row_id="3",
        ),
        _row(
            operation_date=date(2026, 7, 11),
            operation_type=InventoryOperationType.SALE,
            quantity_delta=-2,
            sku="HOLE",
            source_row_id="4",
        ),
    ]
    rebuild_from = date(2026, 7, 6)
    carry = {("A", None, "WH-1")}

    def legacy_keep(m: InventoryLedgerRow) -> bool:
        key = _key(m)
        if key in carry and m.operation_date < rebuild_from:
            return False
        return True

    legacy = [m for m in rows if legacy_keep(m)]
    variant_b = [
        m
        for m in rows
        if row_kept_by_variant_b(
            key=_key(m),
            operation_date=m.operation_date,
            rebuild_from=rebuild_from,
            carry_forward_keys=carry,
        )
    ]
    assert [m.source_row_id for m in legacy] == [m.source_row_id for m in variant_b]
    assert [m.source_row_id for m in variant_b] == ["2", "3", "4"]

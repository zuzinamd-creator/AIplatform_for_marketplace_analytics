from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.domain.inventory.errors import UnsupportedSemanticsVersionError
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.parsers.wb.semantics_registry import (
    OperationSemanticsStrategyV1,
    build_strategy_cache,
    collect_semantics_versions,
)


class InventoryReconstructionService:
    """
    Deterministic daily stock reconstruction from inventory ledger movements.

    expected_closing = opening + inbound - sold + returned - lost - writeoffs
    actual_stock = expected_closing + inventory_adjustment deltas

    Supports rebuild windows: a change on date T requires recomputing T..rebuild_to
    while carrying opening balances from full prior ledger history.
    """

    @staticmethod
    def rebuild_from_ledger(
        movements: list[InventoryLedgerRow],
        *,
        rebuild_from: date | None = None,
        rebuild_to: date | None = None,
        initial_opening: int | None = None,
    ) -> list[WarehouseStockSnapshotDraft]:
        if not movements:
            return []

        strategy_cache = build_strategy_cache(collect_semantics_versions(movements))

        by_key: dict[tuple[str | None, str | None, str | None], list[InventoryLedgerRow]] = (
            defaultdict(list)
        )
        for row in movements:
            key = (row.sku, row.nm_id, row.warehouse_name)
            by_key[key].append(row)

        snapshots: list[WarehouseStockSnapshotDraft] = []
        single_key = len(by_key) == 1
        for key, key_movements in by_key.items():
            key_initial = initial_opening if single_key else None
            snapshots.extend(
                InventoryReconstructionService._rebuild_key(
                    key,
                    key_movements,
                    strategy_cache=strategy_cache,
                    rebuild_from=rebuild_from,
                    rebuild_to=rebuild_to,
                    initial_opening=key_initial,
                ),
            )
        return sorted(
            snapshots,
            key=lambda item: (item.snapshot_date, item.sku or "", item.warehouse_name or ""),
        )

    @staticmethod
    def _rebuild_key(
        key: tuple[str | None, str | None, str | None],
        movements: list[InventoryLedgerRow],
        *,
        strategy_cache: dict[str, OperationSemanticsStrategyV1],
        rebuild_from: date | None,
        rebuild_to: date | None,
        initial_opening: int | None = None,
    ) -> list[WarehouseStockSnapshotDraft]:
        sku, nm_id, warehouse_name = key
        by_date: dict[date, list[InventoryLedgerRow]] = defaultdict(list)
        for row in movements:
            by_date[row.operation_date].append(row)

        opening = initial_opening if initial_opening is not None else 0
        skip_carry_forward = initial_opening is not None
        results: list[WarehouseStockSnapshotDraft] = []
        for snapshot_date in sorted(by_date.keys()):
            if rebuild_to is not None and snapshot_date > rebuild_to:
                break

            day_rows = by_date[snapshot_date]
            inbound, sold, returned, lost, writeoff, adjustment_delta = (
                InventoryReconstructionService._classify_day(day_rows, strategy_cache)
            )
            expected_closing = opening + inbound - sold + returned - lost - writeoff
            actual_stock = expected_closing + adjustment_delta
            discrepancy_units = actual_stock - expected_closing

            if rebuild_from is not None and snapshot_date < rebuild_from:
                if not skip_carry_forward:
                    opening = actual_stock
                continue

            results.append(
                WarehouseStockSnapshotDraft(
                    snapshot_date=snapshot_date,
                    sku=sku,
                    nm_id=nm_id,
                    warehouse_name=warehouse_name,
                    opening_stock=opening,
                    inbound_units=inbound,
                    sold_units=sold,
                    returned_units=returned,
                    lost_units=lost,
                    writeoff_units=writeoff,
                    expected_closing_stock=expected_closing,
                    actual_stock=actual_stock,
                    discrepancy_units=discrepancy_units,
                    discrepancy_cost=Decimal("0"),
                    discrepancy_sale_value=Decimal("0"),
                    semantics_version=_dominant_semantics_version(day_rows),
                )
            )
            opening = actual_stock
        return results

    @staticmethod
    def _classify_day(
        rows: list[InventoryLedgerRow],
        strategy_cache: dict[str, OperationSemanticsStrategyV1],
    ) -> tuple[int, int, int, int, int, int]:
        inbound = 0
        sold = 0
        returned = 0
        lost = 0
        writeoff = 0
        adjustment_delta = 0

        for row in rows:
            strategy = strategy_cache[row.semantics_version]
            buckets = strategy.classify_movement(row)
            inbound += buckets.inbound
            sold += buckets.sold
            returned += buckets.returned
            lost += buckets.lost
            writeoff += buckets.writeoff
            adjustment_delta += buckets.adjustment_delta

        return inbound, sold, returned, lost, writeoff, adjustment_delta


def _dominant_semantics_version(rows: list[InventoryLedgerRow]) -> str:
    versions = collect_semantics_versions(rows)
    if not versions:
        raise UnsupportedSemanticsVersionError("<missing>")
    return max(versions)

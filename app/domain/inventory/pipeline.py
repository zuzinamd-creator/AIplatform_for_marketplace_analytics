from __future__ import annotations

from datetime import date

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.reconciliation import InventoryReconciliationService
from app.domain.inventory.reconstruction import InventoryReconstructionService
from app.domain.inventory.snapshot_types import InventoryLossAnalytics, WarehouseStockSnapshotDraft


class InventorySnapshotPipeline:
    """Deterministic rebuild: ledger -> snapshots -> reconciliation -> loss analytics."""

    @staticmethod
    def rebuild(
        movements: list[InventoryLedgerRow],
        *,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        rebuild_from: date | None = None,
        rebuild_to: date | None = None,
        initial_opening: int | None = None,
    ) -> tuple[list[WarehouseStockSnapshotDraft], InventoryLossAnalytics]:
        window_movements = movements
        if initial_opening is not None and rebuild_from is not None:
            window_movements = [row for row in movements if row.operation_date >= rebuild_from]
        raw_snapshots = InventoryReconstructionService.rebuild_from_ledger(
            window_movements,
            rebuild_from=rebuild_from,
            rebuild_to=rebuild_to,
            initial_opening=initial_opening,
        )
        sale_index = InventoryReconciliationService.build_sale_price_index(window_movements)
        reconciled = InventoryReconciliationService.reconcile_snapshots(
            raw_snapshots,
            costs_by_sku=costs_by_sku,
            sale_prices_by_key=sale_index,
        )
        analytics = InventoryReconciliationService.build_loss_analytics(
            reconciled,
            costs_by_sku=costs_by_sku,
        )
        return reconciled, analytics

"""Compute snapshot drafts from streamed ledger groups."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.reconciliation import InventoryReconciliationService
from app.domain.inventory.snapshot_types import InventoryLossAnalytics, WarehouseStockSnapshotDraft
from app.etl.wb.inventory_ledger_streaming import LedgerKey


class InventorySnapshotComputeService:
    @staticmethod
    async def compute_from_stream(
        stream: AsyncIterator[tuple[LedgerKey, list[InventoryLedgerRow]]],
        *,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        rebuild_from: date,
        rebuild_to: date,
        carry_forward: dict[LedgerKey, int],
    ) -> tuple[list[WarehouseStockSnapshotDraft], InventoryLossAnalytics | None]:
        snapshots: list[WarehouseStockSnapshotDraft] = []
        async for key, key_movements in stream:
            chunk_snapshots, _ = InventorySnapshotPipeline.rebuild(
                key_movements,
                costs_by_sku=costs_by_sku,
                rebuild_from=rebuild_from,
                rebuild_to=rebuild_to,
                initial_opening=carry_forward.get(key),
            )
            snapshots.extend(chunk_snapshots)
        if not snapshots:
            return [], None
        return snapshots, InventoryReconciliationService.build_loss_analytics(
            snapshots,
            costs_by_sku=costs_by_sku,
        )

    @staticmethod
    async def compute_full_from_stream(
        stream: AsyncIterator[tuple[LedgerKey, list[InventoryLedgerRow]]],
        *,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        rebuild_from: date,
        rebuild_to: date,
    ) -> tuple[list[WarehouseStockSnapshotDraft], InventoryLossAnalytics | None]:
        """Ledger-only replay: no carry-forward, opening derived from full history."""
        snapshots: list[WarehouseStockSnapshotDraft] = []
        async for _key, key_movements in stream:
            chunk_snapshots, _ = InventorySnapshotPipeline.rebuild(
                key_movements,
                costs_by_sku=costs_by_sku,
                rebuild_from=rebuild_from,
                rebuild_to=rebuild_to,
                initial_opening=None,
            )
            snapshots.extend(chunk_snapshots)
        if not snapshots:
            return [], None
        return snapshots, InventoryReconciliationService.build_loss_analytics(
            snapshots,
            costs_by_sku=costs_by_sku,
        )

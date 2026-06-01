"""
Full deterministic inventory snapshot rebuild (ledger is sole source of truth).

No carry-forward from prior snapshots. Atomic promote via staging table so readers
never observe an empty or partial live snapshot set within a committed transaction.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.inventory_rebuild_lock import acquire_inventory_rebuild_lock
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.snapshot_types import InventoryLossAnalytics
from app.etl.wb.inventory_ledger_streaming import InventoryLedgerStreamingService
from app.etl.wb.inventory_snapshot_compute import InventorySnapshotComputeService
from app.etl.wb.inventory_snapshot_store import InventorySnapshotStore
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry


class FullInventoryRebuildService:
    """
    Rebuild all warehouse snapshots from inventory_ledger_entries only.

    Caller must run inside a single DB transaction with tenant RLS context set.
    """

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self._stream = InventoryLedgerStreamingService(db, user_id)
        self._store = InventorySnapshotStore(db, user_id)

    async def rebuild(self) -> InventoryLossAnalytics | None:
        await acquire_inventory_rebuild_lock(self.db, self.user_id)

        bounds = await self._ledger_date_bounds()
        if bounds is None:
            return None
        min_date, max_date = bounds
        rebuild_run_id = uuid4()

        await self._store.clear_staging_run(rebuild_run_id)

        costs = await self._load_cost_snapshots()
        stream = self._stream.stream_grouped_by_key(
            rebuild_from=None,
            carry_forward_keys=set(),
        )
        snapshots, analytics = await InventorySnapshotComputeService.compute_full_from_stream(
            stream,
            costs_by_sku=costs,
            rebuild_from=min_date,
            rebuild_to=max_date,
        )

        if snapshots:
            await self._store.insert_staging_batch(snapshots, rebuild_run_id=rebuild_run_id)
            await self._store.promote_staging_to_live(rebuild_run_id)
            await self._store.clear_staging_run(rebuild_run_id)

        return analytics

    async def _ledger_date_bounds(self) -> tuple | None:
        result = await self.db.execute(
            select(
                func.min(InventoryLedgerEntry.operation_date),
                func.max(InventoryLedgerEntry.operation_date),
            ).where(InventoryLedgerEntry.user_id == self.user_id)
        )
        row = result.one()
        if row[0] is None or row[1] is None:
            return None
        return row[0], row[1]

    async def _load_cost_snapshots(self) -> dict[str, list[SkuCostSnapshot]]:
        result = await self.db.execute(
            select(CostHistory).where(CostHistory.user_id == self.user_id)
        )
        costs: dict[str, list[SkuCostSnapshot]] = {}
        for row in result.scalars().all():
            costs.setdefault(row.internal_sku, []).append(
                SkuCostSnapshot(
                    sku=row.internal_sku,
                    effective_from=row.effective_from,
                    product_cost=row.product_cost,
                    packaging_cost=row.packaging_cost,
                    inbound_logistics_cost=row.inbound_logistics_cost,
                    additional_cost=row.additional_cost,
                    currency=row.currency,
                )
            )
        return costs

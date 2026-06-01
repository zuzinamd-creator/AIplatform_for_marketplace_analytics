"""Persistence helpers for warehouse snapshots (live + staging)."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.invariants import check_promote_staging_row_match, check_snapshot_draft_batch
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches
from app.models.inventory import WarehouseStockSnapshot
from app.models.inventory.staging import WarehouseStockSnapshotStaging

LedgerKey = tuple[str | None, str | None, str | None]


class InventorySnapshotStore:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def load_carry_forward_openings(self, rebuild_from: date) -> dict[LedgerKey, int]:
        stmt = (
            select(WarehouseStockSnapshot)
            .where(
                WarehouseStockSnapshot.user_id == self.user_id,
                WarehouseStockSnapshot.snapshot_date < rebuild_from,
            )
            .order_by(
                WarehouseStockSnapshot.sku.asc().nulls_first(),
                WarehouseStockSnapshot.warehouse_name.asc().nulls_first(),
                WarehouseStockSnapshot.nm_id.asc().nulls_first(),
                WarehouseStockSnapshot.snapshot_date.desc(),
            )
        )
        result = await self.db.execute(stmt)
        carry: dict[LedgerKey, int] = {}
        for snap in result.scalars():
            key: LedgerKey = (snap.sku, snap.nm_id, snap.warehouse_name)
            if key not in carry:
                carry[key] = snap.actual_stock
        return carry

    async def delete_window(self, rebuild_from: date, rebuild_to: date) -> None:
        await self.db.execute(
            delete(WarehouseStockSnapshot).where(
                WarehouseStockSnapshot.user_id == self.user_id,
                WarehouseStockSnapshot.snapshot_date >= rebuild_from,
                WarehouseStockSnapshot.snapshot_date <= rebuild_to,
            )
        )

    async def delete_all(self) -> None:
        await self.db.execute(
            delete(WarehouseStockSnapshot).where(WarehouseStockSnapshot.user_id == self.user_id)
        )

    async def upsert_snapshots(self, snapshots: list[WarehouseStockSnapshotDraft]) -> None:
        if not snapshots:
            return
        check_snapshot_draft_batch(snapshots, user_id=self.user_id, stage="upsert_snapshots")
        values = [_draft_to_values(self.user_id, snap) for snap in snapshots]
        upsert = insert(WarehouseStockSnapshot)
        upsert = upsert.on_conflict_do_update(
            constraint="uq_warehouse_stock_snapshot_day_sku_wh",
            set_={
                "nm_id": upsert.excluded.nm_id,
                "opening_stock": upsert.excluded.opening_stock,
                "inbound_units": upsert.excluded.inbound_units,
                "sold_units": upsert.excluded.sold_units,
                "returned_units": upsert.excluded.returned_units,
                "lost_units": upsert.excluded.lost_units,
                "writeoff_units": upsert.excluded.writeoff_units,
                "expected_closing_stock": upsert.excluded.expected_closing_stock,
                "actual_stock": upsert.excluded.actual_stock,
                "discrepancy_units": upsert.excluded.discrepancy_units,
                "discrepancy_cost": upsert.excluded.discrepancy_cost,
                "discrepancy_sale_value": upsert.excluded.discrepancy_sale_value,
                "semantics_version": upsert.excluded.semantics_version,
            },
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(upsert, batch)

    async def insert_staging_batch(
        self,
        snapshots: list[WarehouseStockSnapshotDraft],
        *,
        rebuild_run_id: UUID,
    ) -> None:
        if not snapshots:
            return
        check_snapshot_draft_batch(snapshots, user_id=self.user_id, stage="insert_staging_batch")
        values = [
            {**_draft_to_values(self.user_id, snap), "rebuild_run_id": rebuild_run_id}
            for snap in snapshots
        ]
        stmt = insert(WarehouseStockSnapshotStaging)
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(stmt, batch)

    async def clear_staging_run(self, rebuild_run_id: UUID) -> None:
        await self.db.execute(
            delete(WarehouseStockSnapshotStaging).where(
                WarehouseStockSnapshotStaging.user_id == self.user_id,
                WarehouseStockSnapshotStaging.rebuild_run_id == rebuild_run_id,
            )
        )

    async def promote_staging_to_live(self, rebuild_run_id: UUID) -> None:
        """Replace all live snapshots from staging (atomic within caller transaction)."""
        await self.delete_all()
        columns = [
            WarehouseStockSnapshot.id,
            WarehouseStockSnapshot.user_id,
            WarehouseStockSnapshot.snapshot_date,
            WarehouseStockSnapshot.sku,
            WarehouseStockSnapshot.nm_id,
            WarehouseStockSnapshot.warehouse_name,
            WarehouseStockSnapshot.opening_stock,
            WarehouseStockSnapshot.inbound_units,
            WarehouseStockSnapshot.sold_units,
            WarehouseStockSnapshot.returned_units,
            WarehouseStockSnapshot.lost_units,
            WarehouseStockSnapshot.writeoff_units,
            WarehouseStockSnapshot.expected_closing_stock,
            WarehouseStockSnapshot.actual_stock,
            WarehouseStockSnapshot.discrepancy_units,
            WarehouseStockSnapshot.discrepancy_cost,
            WarehouseStockSnapshot.discrepancy_sale_value,
            WarehouseStockSnapshot.semantics_version,
        ]
        staging_select = select(
            WarehouseStockSnapshotStaging.id,
            WarehouseStockSnapshotStaging.user_id,
            WarehouseStockSnapshotStaging.snapshot_date,
            WarehouseStockSnapshotStaging.sku,
            WarehouseStockSnapshotStaging.nm_id,
            WarehouseStockSnapshotStaging.warehouse_name,
            WarehouseStockSnapshotStaging.opening_stock,
            WarehouseStockSnapshotStaging.inbound_units,
            WarehouseStockSnapshotStaging.sold_units,
            WarehouseStockSnapshotStaging.returned_units,
            WarehouseStockSnapshotStaging.lost_units,
            WarehouseStockSnapshotStaging.writeoff_units,
            WarehouseStockSnapshotStaging.expected_closing_stock,
            WarehouseStockSnapshotStaging.actual_stock,
            WarehouseStockSnapshotStaging.discrepancy_units,
            WarehouseStockSnapshotStaging.discrepancy_cost,
            WarehouseStockSnapshotStaging.discrepancy_sale_value,
            WarehouseStockSnapshotStaging.semantics_version,
        ).where(
            WarehouseStockSnapshotStaging.user_id == self.user_id,
            WarehouseStockSnapshotStaging.rebuild_run_id == rebuild_run_id,
        )
        await self.db.execute(insert(WarehouseStockSnapshot).from_select(columns, staging_select))
        await check_promote_staging_row_match(self.db, self.user_id, rebuild_run_id)

    async def latest_snapshot_date(self) -> date | None:
        result = await self.db.execute(
            select(func.max(WarehouseStockSnapshot.snapshot_date)).where(
                WarehouseStockSnapshot.user_id == self.user_id
            )
        )
        return result.scalar_one_or_none()


def _draft_to_values(user_id: UUID, snap: WarehouseStockSnapshotDraft) -> dict:
    return {
        "id": uuid4(),
        "user_id": user_id,
        "snapshot_date": snap.snapshot_date,
        "sku": snap.sku or "",
        "nm_id": snap.nm_id,
        "warehouse_name": snap.warehouse_name or "",
        "opening_stock": snap.opening_stock,
        "inbound_units": snap.inbound_units,
        "sold_units": snap.sold_units,
        "returned_units": snap.returned_units,
        "lost_units": snap.lost_units,
        "writeoff_units": snap.writeoff_units,
        "expected_closing_stock": snap.expected_closing_stock,
        "actual_stock": snap.actual_stock,
        "discrepancy_units": snap.discrepancy_units,
        "discrepancy_cost": snap.discrepancy_cost,
        "discrepancy_sale_value": snap.discrepancy_sale_value,
        "semantics_version": snap.semantics_version,
    }

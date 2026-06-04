from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.inventory_rebuild_lock import acquire_inventory_rebuild_lock
from app.core.observability.etl_metrics import record_metrics, track_rebuild
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.errors import InventoryRebuildBusyError
from app.domain.inventory.opening_balance import (
    earliest_first_ledger_date,
    is_opening_balance_movement,
    opening_effective_date,
    validate_opening_balance_integrity,
)
from app.domain.inventory.rebuild_window import compute_rebuild_window
from app.domain.inventory.snapshot_types import InventoryLossAnalytics
from app.domain.inventory.types import InventoryMovementDraft
from app.etl.db_batch import INSERT_BATCH_SIZE
from app.etl.wb.inventory_ledger_streaming import InventoryLedgerStreamingService
from app.etl.wb.inventory_snapshot_compute import InventorySnapshotComputeService
from app.etl.wb.inventory_snapshot_store import InventorySnapshotStore
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry


class InventorySnapshotRebuildService:
    """
    Incremental snapshot rebuild: advisory lock, window delete, carry-forward, stream replay.

    Caller must run inside a single DB transaction (e.g. TenantSession.transaction).
    For ledger-only full rebuild without snapshot reuse, use FullInventoryRebuildService.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self._stream = InventoryLedgerStreamingService(db, user_id)
        self._store = InventorySnapshotStore(db, user_id)

    async def validate_opening_balances_for_movements(
        self,
        movements: list[InventoryMovementDraft],
        *,
        exclude_report_id: UUID | None = None,
    ) -> None:
        batch_first_dates = self._batch_first_operation_dates(movements)
        opening_movements = [
            movement
            for movement in movements
            if is_opening_balance_movement(movement.canonical_payload)
        ]
        await self._validate_opening_balance_movements(
            opening_movements,
            batch_first_dates,
            exclude_report_id=exclude_report_id,
        )

    async def validate_opening_balances_streamed(
        self,
        opening_movements: list[InventoryMovementDraft],
        batch_first_dates: dict[tuple[str | None, str | None], date],
        *,
        exclude_report_id: UUID | None = None,
    ) -> None:
        """Opening-balance checks after stream parse (no full movement list in RAM)."""
        await self._validate_opening_balance_movements(
            opening_movements,
            batch_first_dates,
            exclude_report_id=exclude_report_id,
        )

    async def _validate_opening_balance_movements(
        self,
        opening_movements: list[InventoryMovementDraft],
        batch_first_dates: dict[tuple[str | None, str | None], date],
        *,
        exclude_report_id: UUID | None = None,
    ) -> None:
        opening_keys = {
            (movement.sku, movement.warehouse_name)
            for movement in opening_movements
            if movement.sku
        }
        persisted_first_by_key = await self._batch_first_ledger_operation_dates(
            opening_keys,
            exclude_report_id=exclude_report_id,
        )
        for movement in opening_movements:
            effective = opening_effective_date(
                movement.canonical_payload,
                fallback=movement.operation_date,
            )
            sku = movement.sku
            if not sku:
                validate_opening_balance_integrity(
                    opening_date=effective,
                    sku=None,
                    warehouse_name=movement.warehouse_name,
                    first_ledger_operation_date=None,
                )
                continue
            persisted_first = persisted_first_by_key.get((sku, movement.warehouse_name))
            batch_first = batch_first_dates.get((sku, movement.warehouse_name))
            first_date = earliest_first_ledger_date(persisted_first, batch_first)
            validate_opening_balance_integrity(
                opening_date=effective,
                sku=sku,
                warehouse_name=movement.warehouse_name,
                first_ledger_operation_date=first_date,
            )

    @staticmethod
    def _batch_first_operation_dates(
        movements: list[InventoryMovementDraft],
    ) -> dict[tuple[str | None, str | None], date]:
        first_dates: dict[tuple[str | None, str | None], date] = {}
        for movement in movements:
            if not movement.sku:
                continue
            if is_opening_balance_movement(movement.canonical_payload):
                continue
            key = (movement.sku, movement.warehouse_name)
            existing = first_dates.get(key)
            if existing is None or movement.operation_date < existing:
                first_dates[key] = movement.operation_date
        return first_dates

    async def rebuild(
        self,
        *,
        earliest_affected_date: date | None = None,
    ) -> InventoryLossAnalytics | None:
        window_label = "pending"
        try:
            await acquire_inventory_rebuild_lock(self.db, self.user_id)
        except InventoryRebuildBusyError:
            record_metrics(advisory_lock_contention=1)
            raise

        ledger_bounds = await self._ledger_date_bounds()
        if ledger_bounds is None:
            return None
        min_ledger_date, max_ledger_date = ledger_bounds

        latest_snapshot_date = await self._store.latest_snapshot_date()
        if earliest_affected_date is None:
            earliest_affected_date = min_ledger_date

        window = compute_rebuild_window(
            earliest_affected_date=earliest_affected_date,
            latest_snapshot_date=latest_snapshot_date,
            latest_ledger_date=max_ledger_date,
        )
        window_label = f"{window.rebuild_from.isoformat()}..{window.rebuild_to.isoformat()}"

        with track_rebuild(
            mode="incremental",
            user_id=str(self.user_id),
            rebuild_window=window_label,
        ):
            await self._store.delete_window(window.rebuild_from, window.rebuild_to)

            costs = await self._load_cost_snapshots()
            carry_forward = await self._store.load_carry_forward_openings(window.rebuild_from)
            stream = self._stream.stream_grouped_by_key(
                rebuild_from=window.rebuild_from,
                carry_forward_keys=set(carry_forward.keys()),
            )
            snapshots, analytics = await InventorySnapshotComputeService.compute_from_stream(
                stream,
                costs_by_sku=costs,
                rebuild_from=window.rebuild_from,
                rebuild_to=window.rebuild_to,
                carry_forward=carry_forward,
            )

            if not snapshots and latest_snapshot_date is None:
                return None

            if snapshots:
                await self._store.upsert_snapshots(snapshots)
                record_metrics(
                    snapshot_rows_written=len(snapshots),
                    bulk_upsert_batch_size=INSERT_BATCH_SIZE,
                    stream_chunk_size=INSERT_BATCH_SIZE,
                )

            return analytics

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

    async def _ledger_date_bounds(self) -> tuple[date, date] | None:
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

    async def _batch_first_ledger_operation_dates(
        self,
        keys: set[tuple[str, str | None]],
        *,
        exclude_report_id: UUID | None,
    ) -> dict[tuple[str, str | None], date]:
        if not keys:
            return {}
        skus = {sku for sku, _ in keys}
        stmt = (
            select(
                InventoryLedgerEntry.sku,
                InventoryLedgerEntry.warehouse_name,
                func.min(InventoryLedgerEntry.operation_date),
            )
            .where(
                InventoryLedgerEntry.user_id == self.user_id,
                InventoryLedgerEntry.sku.in_(skus),
            )
            .group_by(InventoryLedgerEntry.sku, InventoryLedgerEntry.warehouse_name)
        )
        if exclude_report_id is not None:
            stmt = stmt.where(InventoryLedgerEntry.report_id != exclude_report_id)
        result = await self.db.execute(stmt)
        out: dict[tuple[str, str | None], date] = {}
        for sku, warehouse_name, first_date in result.all():
            if first_date is not None:
                out[(sku, warehouse_name)] = first_date
        return out

    async def _first_ledger_operation_date(
        self,
        *,
        sku: str,
        warehouse_name: str | None,
        exclude_report_id: UUID | None,
    ) -> date | None:
        stmt = select(func.min(InventoryLedgerEntry.operation_date)).where(
            InventoryLedgerEntry.user_id == self.user_id,
            InventoryLedgerEntry.sku == sku,
        )
        if warehouse_name is None:
            stmt = stmt.where(InventoryLedgerEntry.warehouse_name.is_(None))
        else:
            stmt = stmt.where(InventoryLedgerEntry.warehouse_name == warehouse_name)
        if exclude_report_id is not None:
            stmt = stmt.where(InventoryLedgerEntry.report_id != exclude_report_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

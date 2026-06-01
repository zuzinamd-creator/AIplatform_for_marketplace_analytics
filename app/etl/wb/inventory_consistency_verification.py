"""
Nightly-style snapshot drift verification (ledger replay vs persisted snapshots).

Does not mutate live snapshots; records snapshot_consistency_checks and anomalies.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.snapshot_fingerprint import (
    fingerprint_from_draft,
    fingerprint_from_model,
    ledger_day_fingerprint,
)
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.etl.wb.inventory_integrity_escalation import InventoryIntegrityEscalationService
from app.etl.wb.inventory_ledger_streaming import InventoryLedgerStreamingService
from app.models.cost_history import CostHistory
from app.models.inventory import WarehouseStockSnapshot
from app.models.inventory.integrity import InventoryIntegrityAnomalyType, SnapshotConsistencyCheck


@dataclass(frozen=True)
class VerificationSummary:
    checked: int
    consistent: int
    drifted: int


class InventoryConsistencyVerificationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self._stream = InventoryLedgerStreamingService(db, user_id)
        self._escalation = InventoryIntegrityEscalationService(db, user_id)

    async def verify_full(self) -> VerificationSummary:
        """Replay ledger per key and compare all persisted snapshot days."""
        costs = await self._load_cost_snapshots()
        replayed = await self._replay_all_keys(costs)
        persisted = await self._load_persisted_snapshots()
        return await self._compare_and_persist(replayed, persisted)

    async def verify_sample(self, *, max_keys: int = 50, seed: int = 42) -> VerificationSummary:
        """Sample snapshot keys for drift detection."""
        persisted = await self._load_persisted_snapshots()
        if not persisted:
            return VerificationSummary(checked=0, consistent=0, drifted=0)
        keys = list(persisted.keys())
        rng = random.Random(seed)
        if len(keys) > max_keys:
            keys = rng.sample(keys, max_keys)
        costs = await self._load_cost_snapshots()
        replayed: dict[tuple[date, str, str], WarehouseStockSnapshotDraft] = {}
        for snapshot_date, sku, warehouse_name in keys:
            draft = await self._replay_single_key(
                costs,
                snapshot_date=snapshot_date,
                sku=sku,
                warehouse_name=warehouse_name,
            )
            if draft is not None:
                replayed[(snapshot_date, sku, warehouse_name)] = draft
        filtered = {key: persisted[key] for key in keys if key in persisted}
        return await self._compare_and_persist(replayed, filtered)

    async def _replay_all_keys(
        self,
        costs: dict[str, list[SkuCostSnapshot]],
    ) -> dict[tuple[date, str, str], WarehouseStockSnapshotDraft]:
        by_key_rows: dict[tuple[str, str], list[InventoryLedgerRow]] = defaultdict(list)
        async for ledger_key, rows in self._stream.stream_grouped_by_key():
            sku = ledger_key[0] or ""
            warehouse = ledger_key[2] or ""
            by_key_rows[(sku, warehouse)].extend(rows)

        replayed: dict[tuple[date, str, str], WarehouseStockSnapshotDraft] = {}
        for (_sku, _warehouse), rows in by_key_rows.items():
            if not rows:
                continue
            min_date = min(row.operation_date for row in rows)
            max_date = max(row.operation_date for row in rows)
            snapshots, _ = InventorySnapshotPipeline.rebuild(
                rows,
                costs_by_sku=costs,
                rebuild_from=min_date,
                rebuild_to=max_date,
                initial_opening=None,
            )
            for snap in snapshots:
                replayed[(snap.snapshot_date, snap.sku or "", snap.warehouse_name or "")] = snap
        return replayed

    async def _replay_single_key(
        self,
        costs: dict[str, list[SkuCostSnapshot]],
        *,
        snapshot_date: date,
        sku: str,
        warehouse_name: str,
    ) -> WarehouseStockSnapshotDraft | None:
        rows: list[InventoryLedgerRow] = []
        async for ledger_key, key_rows in self._stream.stream_grouped_by_key():
            if (ledger_key[0] or "") != sku or (ledger_key[2] or "") != warehouse_name:
                continue
            rows.extend(key_rows)
        if not rows:
            return None
        min_date = min(row.operation_date for row in rows)
        max_date = max(row.operation_date for row in rows)
        snapshots, _ = InventorySnapshotPipeline.rebuild(
            rows,
            costs_by_sku=costs,
            rebuild_from=min_date,
            rebuild_to=max_date,
            initial_opening=None,
        )
        for snap in snapshots:
            if snap.snapshot_date == snapshot_date:
                return snap
        return None

    async def _load_persisted_snapshots(
        self,
    ) -> dict[tuple[date, str, str], WarehouseStockSnapshot]:
        result = await self.db.execute(
            select(WarehouseStockSnapshot).where(WarehouseStockSnapshot.user_id == self.user_id)
        )
        persisted: dict[tuple[date, str, str], WarehouseStockSnapshot] = {}
        for snap in result.scalars().all():
            persisted[(snap.snapshot_date, snap.sku or "", snap.warehouse_name or "")] = snap
        return persisted

    async def _compare_and_persist(
        self,
        replayed: dict[tuple[date, str, str], WarehouseStockSnapshotDraft],
        persisted: dict[tuple[date, str, str], WarehouseStockSnapshot],
    ) -> VerificationSummary:
        checked = 0
        consistent = 0
        drifted = 0
        all_keys = set(replayed) | set(persisted)

        for key in sorted(all_keys):
            snapshot_date, sku, warehouse_name = key
            draft = replayed.get(key)
            live = persisted.get(key)
            day_rows = await self._ledger_rows_for_day(snapshot_date, sku, warehouse_name)
            ledger_hash = ledger_day_fingerprint(day_rows) if day_rows else ""

            if draft is None and live is None:
                continue

            checked += 1
            details: dict | None
            if draft is None or live is None:
                is_ok = False
                details = {"reason": "missing_replay_or_persisted", "key": key}
            else:
                replay_hash = fingerprint_from_draft(draft)
                live_hash = fingerprint_from_model(live)
                is_ok = replay_hash == live_hash
                details = None if is_ok else {
                    "replay_hash": replay_hash,
                    "live_hash": live_hash,
                    "ledger_hash": ledger_hash,
                }

            if is_ok:
                consistent += 1
            else:
                drifted += 1
                await self._escalation.record(
                    anomaly_type=InventoryIntegrityAnomalyType.SNAPSHOT_DRIFT,
                    snapshot_date=snapshot_date,
                    sku=sku or None,
                    warehouse_name=warehouse_name or None,
                    details=details,
                )

            if draft is not None and draft.actual_stock < 0:
                await self._escalation.record(
                    anomaly_type=InventoryIntegrityAnomalyType.NEGATIVE_INVENTORY,
                    snapshot_date=snapshot_date,
                    sku=sku or None,
                    warehouse_name=warehouse_name or None,
                    details={"actual_stock": draft.actual_stock},
                )

            if draft is not None:
                snap_hash = fingerprint_from_draft(draft)
                sem_ver = draft.semantics_version
            elif live is not None:
                snap_hash = fingerprint_from_model(live)
                sem_ver = live.semantics_version
            else:
                snap_hash = ""
                sem_ver = "1.0"
            self.db.add(
                SnapshotConsistencyCheck(
                    id=uuid4(),
                    user_id=self.user_id,
                    snapshot_date=snapshot_date,
                    sku=sku or None,
                    warehouse_name=warehouse_name or None,
                    ledger_hash=ledger_hash,
                    snapshot_hash=snap_hash,
                    semantics_version=sem_ver,
                    is_consistent=is_ok,
                    mismatch_details=details,
                )
            )

        await self.db.flush()
        return VerificationSummary(checked=checked, consistent=consistent, drifted=drifted)

    async def _ledger_rows_for_day(
        self,
        snapshot_date: date,
        sku: str,
        warehouse_name: str,
    ) -> list[InventoryLedgerRow]:
        rows: list[InventoryLedgerRow] = []
        async for ledger_key, key_rows in self._stream.stream_grouped_by_key():
            if (ledger_key[0] or "") != sku or (ledger_key[2] or "") != warehouse_name:
                continue
            rows.extend(row for row in key_rows if row.operation_date == snapshot_date)
        return rows

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

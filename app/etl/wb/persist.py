from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.snapshot_types import InventoryLossAnalytics
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.etl.wb.persist_aggregates import WbPersistAggregatesMixin
from app.etl.wb.persist_layers import WbPersistLayersMixin
from app.etl.wb.types import WbFinancialProcessResult
from app.models.report import Report


class WbFinancialPersistService(WbPersistLayersMixin, WbPersistAggregatesMixin):
    """Persist WB financial layers idempotently under tenant RLS."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def persist(
        self,
        *,
        report: Report,
        file_checksum: str,
        storage_uri: str,
        result: WbFinancialProcessResult,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
    ) -> InventoryLossAnalytics | None:
        snapshot_service = InventorySnapshotRebuildService(self.db, self.user_id)
        await snapshot_service.validate_opening_balances_for_movements(
            result.inventory_movements,
            exclude_report_id=report.id,
        )
        await self._persist_raw_report(
            report=report,
            file_checksum=file_checksum,
            storage_uri=storage_uri,
            result=result,
        )
        await self._persist_normalized_rows(report_id=report.id, result=result)
        await self._persist_ledger(report_id=report.id, result=result)
        await self._persist_inventory_ledger(report_id=report.id, result=result)
        earliest_affected = _earliest_movement_date(result)
        loss_analytics = await snapshot_service.rebuild(earliest_affected_date=earliest_affected)
        await self._persist_reconciliation(report_id=report.id, result=result)
        await self._rebuild_aggregates(result=result, costs_by_sku=costs_by_sku)
        return loss_analytics


def _earliest_movement_date(result: WbFinancialProcessResult) -> date | None:
    if not result.inventory_movements:
        return None
    return min(movement.operation_date for movement in result.inventory_movements)

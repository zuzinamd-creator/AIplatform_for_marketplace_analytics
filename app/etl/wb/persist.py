from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import get_logger
from app.core.security_context import TenantSession
from app.core.queue.etl_retry_policy import EtlRetryableError, RetryReason
from app.etl.pg_timeouts import is_lock_timeout_error, set_local_lock_timeout
from app.etl.worker_shutdown import WorkerShutdownRequested, default_shutdown_check, is_shutdown
from app.domain.inventory.errors import InventoryRebuildBusyError
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.snapshot_types import InventoryLossAnalytics
from app.domain.inventory.types import InventoryMovementDraft
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.etl.wb.persist_aggregates import WbPersistAggregatesMixin
from app.etl.wb.persist_layers import WbPersistLayersMixin
from app.etl.wb.row_counts import assert_row_count, count_phase1_rows
from app.etl.wb.stream_types import WbProcessChunk
from app.etl.wb.types import WbFinancialProcessResult
from app.models.report import Report

logger = get_logger("wb_persist")


class WbFinancialPersistService(WbPersistLayersMixin, WbPersistAggregatesMixin):
    """Persist WB financial layers idempotently under tenant RLS."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def rollback_pending(self) -> None:
        """Drop uncommitted ORM state after a failed chunk (transaction already rolled back)."""
        await self.db.rollback()

    async def persist(
        self,
        *,
        report: Report,
        file_checksum: str,
        storage_uri: str,
        result: WbFinancialProcessResult,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
        job_id: UUID | None = None,
        opening_movements: list[InventoryMovementDraft] | None = None,
        batch_first_dates: dict[tuple[str | None, str | None], date] | None = None,
        in_transaction: bool = False,
    ) -> InventoryLossAnalytics | None:
        """
        Persist in isolated phases (separate commits) to avoid one long DB transaction.

        Streamed jobs persist phase-1 per chunk in the worker; this method runs phases 2–3
        after row-count validation.
        """
        if result.streamed:
            await self._validate_before_persist(
                report=report,
                result=result,
                opening_movements=opening_movements or [],
                batch_first_dates=batch_first_dates or {},
                job_id=job_id,
                in_transaction=in_transaction,
            )
            return await self._persist_phases_2_3(
                report=report,
                result=result,
                costs_by_sku=costs_by_sku,
                job_id=job_id,
                in_transaction=in_transaction,
            )

        return await self._persist_phased(
            report=report,
            file_checksum=file_checksum,
            storage_uri=storage_uri,
            result=result,
            costs_by_sku=costs_by_sku,
            job_id=job_id,
        )

    async def persist_phase1_chunk(
        self,
        *,
        report: Report,
        chunk: WbProcessChunk,
        job_id: UUID | None = None,
    ) -> None:
        """Insert one parse chunk (normalized + ledger + inventory) in a short transaction."""
        async with TenantSession.transaction(self.db, self.user_id):
            await self._persist_phase1_chunk(report_id=report.id, chunk=chunk)
            await self.db.flush()

        logger.info(
            "wb_persist_phase_chunk",
            extra={
                "phase": 1,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
                "chunk_rows": len(chunk.normalized_rows),
            },
        )

    async def persist_raw_report_row(
        self,
        *,
        report: Report,
        file_checksum: str,
        storage_uri: str,
        result: WbFinancialProcessResult,
        job_id: UUID | None = None,
    ) -> None:
        async with TenantSession.transaction(self.db, self.user_id):
            await self._persist_raw_report(
                report=report,
                file_checksum=file_checksum,
                storage_uri=storage_uri,
                result=result,
            )
            await self.db.flush()
        logger.info(
            "wb_persist_raw_report",
            extra={
                "phase": 1,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
                "rows": result.row_count,
            },
        )

    async def _validate_before_persist(
        self,
        *,
        report: Report,
        result: WbFinancialProcessResult,
        opening_movements: list[InventoryMovementDraft],
        batch_first_dates: dict[tuple[str | None, str | None], date],
        job_id: UUID | None,
        in_transaction: bool = False,
    ) -> None:
        norm_count, _, _ = await count_phase1_rows(
            self.db,
            user_id=self.user_id,
            report_id=report.id,
        )
        assert_row_count(
            label="normalized_rows",
            actual=norm_count,
            expected=result.row_count,
            report_id=report.id,
        )
        if report.row_count is not None:
            assert_row_count(
                label="report.row_count",
                actual=result.row_count,
                expected=report.row_count,
                report_id=report.id,
            )
        logger.info(
            "wb_persist_row_count_ok",
            extra={
                "phase": 1,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
                "normalized_rows": norm_count,
                "expected_rows": result.row_count,
            },
        )

        if not in_transaction:
            await self.db.commit()
        snapshot_service = InventorySnapshotRebuildService(self.db, self.user_id)
        if in_transaction:
            await snapshot_service.validate_opening_balances_streamed(
                opening_movements,
                batch_first_dates,
                exclude_report_id=report.id,
            )
        else:
            async with TenantSession.transaction(self.db, self.user_id):
                await snapshot_service.validate_opening_balances_streamed(
                    opening_movements,
                    batch_first_dates,
                    exclude_report_id=report.id,
                )

    async def _persist_phased(
        self,
        *,
        report: Report,
        file_checksum: str,
        storage_uri: str,
        result: WbFinancialProcessResult,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
        job_id: UUID | None = None,
    ) -> InventoryLossAnalytics | None:
        snapshot_service = InventorySnapshotRebuildService(self.db, self.user_id)

        async with TenantSession.transaction(self.db, self.user_id):
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
            await self.db.flush()
        await self._assert_phase1_counts(report=report, result=result, job_id=job_id, phase_label=1)
        logger.info(
            "wb_persist_phase_committed",
            extra={
                "phase": 1,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
                "rows": result.row_count,
            },
        )

        return await self._persist_phases_2_3(
            report=report,
            result=result,
            costs_by_sku=costs_by_sku,
            job_id=job_id,
        )

    async def _persist_phases_2_3(
        self,
        *,
        report: Report,
        result: WbFinancialProcessResult,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
        job_id: UUID | None = None,
        in_transaction: bool = False,
    ) -> InventoryLossAnalytics | None:
        snapshot_service = InventorySnapshotRebuildService(self.db, self.user_id)
        earliest_affected = _earliest_movement_date(result)

        if is_shutdown(default_shutdown_check()):
            raise WorkerShutdownRequested(phase="persist_phase2")

        loss_analytics: InventoryLossAnalytics | None = None

        async def _phase2() -> None:
            nonlocal loss_analytics
            loss_analytics = await snapshot_service.rebuild(earliest_affected_date=earliest_affected)
            await self._persist_reconciliation(report_id=report.id, result=result)
            await self.db.flush()

        if in_transaction:
            await _phase2()
        else:
            async with TenantSession.transaction(self.db, self.user_id):
                await _phase2()
        await self._assert_phase1_counts(report=report, result=result, job_id=job_id, phase_label=2)
        logger.info(
            "wb_persist_phase_committed",
            extra={
                "phase": 2,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
            },
        )

        if is_shutdown(default_shutdown_check()):
            raise WorkerShutdownRequested(phase="persist_phase3")

        async def _phase3() -> None:
            await set_local_lock_timeout(
                self.db,
                timeout_ms=settings.etl_aggregate_lock_timeout_ms,
            )
            try:
                await self._rebuild_aggregates(
                    result=result,
                    report_id=report.id,
                    costs_by_sku=costs_by_sku,
                )
            except InventoryRebuildBusyError as exc:
                raise EtlRetryableError(
                    str(exc),
                    retry_reason=RetryReason.INVENTORY_REBUILD_BUSY,
                ) from exc
            except Exception as exc:
                if is_lock_timeout_error(exc):
                    raise EtlRetryableError(
                        "Aggregate rebuild lock timeout",
                        retry_reason=RetryReason.LOCK_TIMEOUT,
                    ) from exc
                raise
            await self.db.flush()

        if in_transaction:
            await _phase3()
        else:
            async with TenantSession.transaction(self.db, self.user_id):
                await _phase3()
        await self._assert_phase1_counts(report=report, result=result, job_id=job_id, phase_label=3)
        logger.info(
            "wb_persist_phase_committed",
            extra={
                "phase": 3,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
            },
        )

        return loss_analytics

    async def _assert_phase1_counts(
        self,
        *,
        report: Report,
        result: WbFinancialProcessResult,
        job_id: UUID | None,
        phase_label: int,
    ) -> None:
        norm_count, _, _ = await count_phase1_rows(
            self.db,
            user_id=self.user_id,
            report_id=report.id,
        )
        assert_row_count(
            label=f"phase{phase_label}_normalized_rows",
            actual=norm_count,
            expected=result.row_count,
            report_id=report.id,
        )
        logger.info(
            "wb_persist_row_count_ok",
            extra={
                "phase": phase_label,
                "job_id": str(job_id) if job_id else None,
                "report_id": str(report.id),
                "normalized_rows": norm_count,
                "expected_rows": result.row_count,
            },
        )


def _earliest_movement_date(result: WbFinancialProcessResult) -> date | None:
    if result.earliest_movement_date is not None:
        return result.earliest_movement_date
    if not result.inventory_movements:
        return None
    return min(movement.operation_date for movement in result.inventory_movements)

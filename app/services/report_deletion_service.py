"""Tenant-safe report deletion with cascade cleanup and projection rebuild."""

from __future__ import annotations

import asyncio
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import get_logger
from app.etl.storage import delete_report_file
from app.etl.wb.persist import WbFinancialPersistService
from app.models.ai_insights import AIInsight
from app.models.cost_history import CostHistory
from app.models.finance.ledger import FinancialLedgerEntry
from app.models.job import EtlJob, JobStatus
from app.models.report import Report
from app.models.user import User
from app.services.base import TenantScopedService
from app.services.semantics_invalidation_service import SemanticsInvalidationService

logger = get_logger(__name__)


class ReportDeletionService(TenantScopedService):
    def __init__(self, db: AsyncSession, user: User) -> None:
        super().__init__(db, user_id=user.id)
        self.user = user

    async def delete_report(self, report_id: UUID) -> None:
        storage_uri: str | None = None
        async with self._rls_transaction():
            report = await self._get_owned_report(report_id)
            await self._assert_deletable(report_id)
            affected_dates = await self._affected_dates(report_id)
            earliest_date = min(affected_dates) if affected_dates else None
            storage_uri = report.file_path

            await self.db.execute(
                delete(AIInsight).where(
                    AIInsight.user_id == self.user.id,
                    AIInsight.context_payload["report_id"].astext == str(report_id),
                )
            )
            await self.db.execute(
                update(CostHistory)
                .where(
                    CostHistory.user_id == self.user.id,
                    CostHistory.source_report_id == report_id,
                )
                .values(source_report_id=None)
            )
            await self.db.delete(report)

            persist = WbFinancialPersistService(self.db, self.user.id)
            await persist.rebuild_projections_for_dates(affected_dates)
            if earliest_date is not None:
                await SemanticsInvalidationService(self.db, self.user.id).request_rebuild(
                    semantics_version="1.0",
                    reason=f"report_deleted:{report_id}",
                )

        if storage_uri:
            asyncio.create_task(_delete_report_file_best_effort(storage_uri))

    async def _get_owned_report(self, report_id: UUID) -> Report:
        result = await self.db.execute(
            select(Report).where(Report.id == report_id, Report.user_id == self.user.id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        return report

    async def _assert_deletable(self, report_id: UUID) -> None:
        result = await self.db.execute(
            select(EtlJob.status)
            .where(EtlJob.report_id == report_id)
            .order_by(EtlJob.created_at.desc())
            .limit(1)
        )
        latest_status = result.scalar_one_or_none()
        if latest_status == JobStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Report is processing; wait for ETL to finish or fail before deleting",
            )

    async def _affected_dates(self, report_id: UUID) -> set[date]:
        result = await self.db.execute(
            select(FinancialLedgerEntry.operation_date)
            .where(
                FinancialLedgerEntry.user_id == self.user.id,
                FinancialLedgerEntry.report_id == report_id,
            )
            .distinct()
        )
        return {value for (value,) in result.all() if value is not None}


async def _delete_report_file_best_effort(storage_uri: str) -> None:
    try:
        await asyncio.to_thread(delete_report_file, storage_uri)
    except Exception:
        logger.exception("report_file_delete_failed", extra={"storage_uri": storage_uri})

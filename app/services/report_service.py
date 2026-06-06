from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.core.observability import get_logger
from app.core.config import settings
from app.core.queue import EnqueuePayload, get_queue_backend
from app.core.ttl_cache import TtlCache
from app.domain.reports.period_queries import fetch_sale_period_bounds_for_reports
from app.models.job import EtlJob, JobStatus
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.schemas.report import ReportResponse
from app.schemas.report_mappers import report_to_response
from app.schemas.report_projection import report_status_from_job_status
from app.models.user import User
from app.services.base import TenantScopedService


_reports_list_cache: TtlCache[list[ReportResponse]] = TtlCache(ttl_seconds=45)
logger = get_logger(__name__)


class ReportService(TenantScopedService):
    def __init__(self, db: AsyncSession, user: User):
        super().__init__(db, user_id=user.id)
        self.user = user
        self._queue = get_queue_backend(db)

    async def find_by_checksum(self, file_checksum: str) -> Report | None:
        query = select(Report).where(
            Report.file_checksum == file_checksum,
            Report.user_id == self.user.id,
        )
        async with self._rls_transaction():
            result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_report(
        self,
        *,
        marketplace: Marketplace,
        report_type: ReportType,
        original_filename: str,
        file_path: str | None,
        file_checksum: str,
        raw_data: dict | None,
        row_count: int | None,
    ) -> Report:
        report = Report(
            user_id=self.user.id,
            marketplace=marketplace,
            report_type=report_type,
            original_filename=original_filename,
            file_path=file_path,
            file_checksum=file_checksum,
            raw_data=raw_data,
            row_count=row_count,
        )
        async with self._rls_transaction():
            self.db.add(report)
            await self.db.flush()
            await self.db.refresh(report)
        return report

    async def finalize_upload(
        self,
        report: Report,
        storage_path: str,
        *,
        file_size_bytes: int | None = None,
    ) -> EtlJob:
        """Persist storage path and enqueue ETL in one tenant transaction."""
        async with self._rls_transaction():
            report.file_path = storage_path
            self.db.add(report)
            await self.db.flush()
            await self.db.refresh(report)
            if not report.file_checksum or not report.file_path:
                raise ValueError("file_checksum and file_path are required to enqueue ETL job")
            payload = EnqueuePayload(
                user_id=self.user.id,
                report_id=report.id,
                idempotency_key=report.file_checksum,
                file_path=report.file_path,
                marketplace=report.marketplace.value,
                report_type=report.report_type.value,
                original_filename=report.original_filename,
                report_created_at=report.created_at,
                max_attempts=settings.job_max_attempts,
                visibility_timeout_seconds=settings.job_visibility_timeout_seconds,
                file_size_bytes=file_size_bytes,
            )
            job = await self._queue.enqueue(payload)
            await self.db.refresh(job)
            logger.info(
                "report_upload_enqueued",
                extra={
                    "report_id": str(report.id),
                    "user_id": str(self.user.id),
                    "checksum": report.file_checksum,
                    "job_id": str(job.id),
                },
            )
            return job

    async def enqueue_processing(
        self,
        report: Report,
        *,
        file_size_bytes: int | None = None,
    ) -> EtlJob:
        if not report.file_checksum or not report.file_path:
            raise ValueError("file_checksum and file_path are required to enqueue ETL job")

        payload = EnqueuePayload(
            user_id=self.user.id,
            report_id=report.id,
            idempotency_key=report.file_checksum,
            file_path=report.file_path,
            marketplace=report.marketplace.value,
            report_type=report.report_type.value,
            original_filename=report.original_filename,
            report_created_at=report.created_at,
            max_attempts=settings.job_max_attempts,
            visibility_timeout_seconds=settings.job_visibility_timeout_seconds,
            file_size_bytes=file_size_bytes,
        )
        async with self._rls_transaction():
            job = await self._queue.enqueue(payload)
            await self.db.refresh(job)
        return job

    async def list_reports(
        self,
        skip: int = 0,
        limit: int = 200,
    ) -> list[ReportResponse]:
        cache_key = f"{self.user.id}:{skip}:{limit}"
        cached = _reports_list_cache.get(cache_key)
        if cached is not None:
            return cached

        # List view must not load raw_data (~MB per report); period comes from sale rows.
        query = (
            select(Report)
            .options(defer(Report.raw_data))
            .where(Report.user_id == self.user.id)
            .order_by(Report.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        async with self._rls_transaction():
            result = await self.db.execute(query)
            reports = list(result.scalars().all())
            if not reports:
                return []
            report_ids = [r.id for r in reports]
            jobs_by_report = await self._latest_jobs_for_reports(report_ids)
            period_bounds = await self._period_bounds_for_report_ids(report_ids)
            responses = [
                report_to_response(
                    report,
                    jobs_by_report.get(report.id),
                    period_start=period_bounds.get(report.id, (None, None))[0],
                    period_end=period_bounds.get(report.id, (None, None))[1],
                )
                for report in reports
            ]
        _reports_list_cache.set(cache_key, responses)
        return responses

    def invalidate_list_cache(self) -> None:
        _reports_list_cache.invalidate_prefix(f"{self.user.id}:")

    async def _period_bounds_for_reports(
        self,
        report_ids: list[UUID],
    ) -> dict[UUID, tuple[date | None, date | None]]:
        async with self._rls_transaction():
            return await self._period_bounds_for_report_ids(report_ids)

    async def _period_bounds_for_report_ids(
        self,
        report_ids: list[UUID],
    ) -> dict[UUID, tuple[date | None, date | None]]:
        return await fetch_sale_period_bounds_for_reports(self.db, report_ids)

    async def get_report(self, report_id: UUID) -> tuple[Report, EtlJob | None, date | None, date | None]:
        query = select(Report).where(Report.id == report_id, Report.user_id == self.user.id)
        async with self._rls_transaction():
            result = await self.db.execute(query)
            report = result.scalar_one_or_none()
            if not report:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
            jobs_by_report = await self._latest_jobs_for_reports([report.id])
            period_bounds = await self._period_bounds_for_report_ids([report.id])
        job = jobs_by_report.get(report.id)
        ps, pe = period_bounds.get(report.id, (None, None))
        return report, job, ps, pe

    async def _latest_job(self, report_id: UUID) -> EtlJob | None:
        async with self._rls_transaction():
            jobs = await self._latest_jobs_for_reports([report_id])
        return jobs.get(report_id)

    async def _latest_jobs_for_reports(self, report_ids: list[UUID]) -> dict[UUID, EtlJob]:
        if not report_ids:
            return {}
        latest_created = (
            select(
                EtlJob.report_id.label("report_id"),
                func.max(EtlJob.created_at).label("max_created_at"),
            )
            .where(EtlJob.report_id.in_(report_ids))
            .group_by(EtlJob.report_id)
            .subquery()
        )
        query = select(EtlJob).join(
            latest_created,
            (EtlJob.report_id == latest_created.c.report_id)
            & (EtlJob.created_at == latest_created.c.max_created_at),
        )
        result = await self.db.execute(query)
        return {job.report_id: job for job in result.scalars().all()}

    async def persist_business_result(
        self,
        report: Report,
        *,
        raw_data: dict,
        row_count: int,
        in_transaction: bool = False,
    ) -> Report:
        """Update report domain fields only (no processing status)."""
        if in_transaction:
            report.raw_data = raw_data
            report.row_count = row_count
            report.processed_at = datetime.now(UTC)
            self.db.add(report)
            await self.db.flush()
            await self.db.refresh(report)
        else:
            async with self._rls_transaction():
                report.raw_data = raw_data
                report.row_count = row_count
                report.processed_at = datetime.now(UTC)
                self.db.add(report)
                await self.db.flush()
                await self.db.refresh(report)
        return report

    async def _sync_report_status(self, report_id: UUID, job_status: JobStatus) -> None:
        target = report_status_from_job_status(job_status)
        result = await self.db.execute(
            select(Report).where(Report.id == report_id, Report.user_id == self.user.id)
        )
        report = result.scalar_one_or_none()
        if report is None or report.status == target:
            return
        report.status = target
        if job_status == JobStatus.COMPLETED and report.processed_at is None:
            report.processed_at = datetime.now(UTC)
        self.db.add(report)

    async def ack_job(self, job_id: UUID, *, report_id: UUID | None = None, in_transaction: bool = False) -> None:
        async def _run() -> None:
            await self._queue.ack(str(job_id))
            rid = report_id
            if rid is None:
                job_row = await self.db.execute(select(EtlJob.report_id).where(EtlJob.id == job_id))
                rid = job_row.scalar_one_or_none()
            if rid is not None:
                await self._sync_report_status(rid, JobStatus.COMPLETED)

        if in_transaction:
            await _run()
        else:
            async with self._rls_transaction():
                await _run()

    async def fail_job(
        self,
        job_id: UUID,
        *,
        error_message: str,
        attempt_count: int,
        max_attempts: int,
        in_transaction: bool = False,
        retry_reason: str | None = None,
    ) -> None:
        from app.core.queue.etl_retry_policy import RetryReason, classify_retry_reason

        poison = attempt_count >= max_attempts
        reason = (
            RetryReason(retry_reason)
            if retry_reason
            else classify_retry_reason(error_message)
        )

        async def _apply() -> None:
            await self._queue.fail(
                str(job_id),
                error_message=error_message,
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                poison=poison,
                retry_reason=reason,
            )
            job_row = await self.db.execute(
                select(EtlJob.report_id, EtlJob.status).where(EtlJob.id == job_id)
            )
            row = job_row.one_or_none()
            if row is not None:
                await self._sync_report_status(row.report_id, row.status)

        if in_transaction:
            await _apply()
        else:
            async with self._rls_transaction():
                await _apply()

    async def heartbeat_job(self, job_id: UUID, *, in_transaction: bool = False) -> None:
        if in_transaction:
            await self._queue.heartbeat(str(job_id))
        else:
            async with self._rls_transaction():
                await self._queue.heartbeat(str(job_id))

    async def retry_processing(self, report_id: UUID) -> ReportResponse:
        """Requeue a failed/dead-letter ETL job for the tenant's report."""
        from app.core.security_context import QueueSession, TenantSession
        from app.operations.recovery import TenantRecoveryService

        report, job, period_start, period_end = await self.get_report(report_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No ETL job found for this report",
            )
        if not is_report_retryable(job):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Report is not in a failed state",
            )

        if job.status == JobStatus.DEAD_LETTER:
            result = await TenantRecoveryService(self.db, self.user.id).replay_dead_letter_job(
                job.id,
                reset_attempt_counter=True,
            )
            if result.affected_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=result.detail,
                )
        else:
            async with TenantSession.transaction(self.db, self.user.id):
                row = await self.db.get(EtlJob, job.id)
                if row is None or row.user_id != self.user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="ETL job not found",
                    )
                row.attempt_count = 0
                row.status = JobStatus.PENDING
                row.last_error = None
                row.claimed_at = None
                row.processing_started_at = None
                row.completed_at = None
                await self._sync_report_status(report_id, JobStatus.PENDING)
            async with QueueSession.transaction(self.db):
                await get_queue_backend(self.db).requeue(str(job.id))

        self.invalidate_list_cache()
        logger.info(
            "report_retry_queued",
            extra={"report_id": str(report_id), "job_id": str(job.id)},
        )
        report, job, period_start, period_end = await self.get_report(report_id)
        return report_to_response(
            report,
            job,
            period_start=period_start,
            period_end=period_end,
        )

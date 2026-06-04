from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.queue import EnqueuePayload, get_queue_backend
from app.models.job import EtlJob
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from app.services.base import TenantScopedService


class ReportService(TenantScopedService):
    def __init__(self, db: AsyncSession, user: User):
        super().__init__(db, user_id=user.id)
        self.user = user
        self._queue = get_queue_backend(db)

    async def find_by_checksum(self, file_checksum: str) -> Report | None:
        query = select(Report).where(Report.file_checksum == file_checksum)
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
        limit: int = 50,
    ) -> list[tuple[Report, EtlJob | None]]:
        query = select(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit)
        async with self._rls_transaction():
            result = await self.db.execute(query)
            reports = list(result.scalars().all())
        return [(report, await self._latest_job(report.id)) for report in reports]

    async def get_report(self, report_id: UUID) -> tuple[Report, EtlJob | None]:
        query = select(Report).where(Report.id == report_id)
        async with self._rls_transaction():
            result = await self.db.execute(query)
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        return report, await self._latest_job(report.id)

    async def _latest_job(self, report_id: UUID) -> EtlJob | None:
        query = (
            select(EtlJob)
            .where(EtlJob.report_id == report_id)
            .order_by(EtlJob.created_at.desc())
            .limit(1)
        )
        async with self._rls_transaction():
            result = await self.db.execute(query)
        return result.scalar_one_or_none()

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

    async def ack_job(self, job_id: UUID, *, in_transaction: bool = False) -> None:
        if in_transaction:
            await self._queue.ack(str(job_id))
        else:
            async with self._rls_transaction():
                await self._queue.ack(str(job_id))

    async def fail_job(
        self,
        job_id: UUID,
        *,
        error_message: str,
        attempt_count: int,
        max_attempts: int,
        in_transaction: bool = False,
    ) -> None:
        poison = attempt_count >= max_attempts

        async def _apply() -> None:
            await self._queue.fail(
                str(job_id),
                error_message=error_message,
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                poison=poison,
            )

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

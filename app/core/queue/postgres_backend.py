from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue.etl_retry_policy import (
    RetryReason,
    compute_etl_retry_eligible_at,
    retry_audit_extra,
)
from app.core.queue.stale import is_etl_job_stale
from app.core.observability import get_logger
from app.core.queue.types import ClaimedJobRecord, EnqueuePayload, RecoveryRecord
from app.core.security_context import QueueSession
from app.models.job import EtlJob, JobStatus

_queue_logger = get_logger("queue")


class PostgresQueueBackend:
    """PostgreSQL SKIP LOCKED queue on etl_jobs (queue_role for claim/recover)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enqueue(self, payload: EnqueuePayload) -> EtlJob:
        existing = await self.db.execute(
            select(EtlJob).where(
                EtlJob.user_id == payload.user_id,
                EtlJob.idempotency_key == payload.idempotency_key,
                EtlJob.status.in_(
                    [JobStatus.PENDING, JobStatus.PROCESSING],
                ),
            )
        )
        active = existing.scalar_one_or_none()
        if active is not None:
            return active

        job = EtlJob(
            user_id=payload.user_id,
            report_id=payload.report_id,
            job_type=payload.job_type,
            status=JobStatus.PENDING,
            idempotency_key=payload.idempotency_key,
            max_attempts=payload.max_attempts,
            visibility_timeout_seconds=payload.visibility_timeout_seconds,
            file_path=payload.file_path,
            marketplace=payload.marketplace,
            report_type=payload.report_type,
            original_filename=payload.original_filename,
            report_created_at=payload.report_created_at,
            file_size_bytes=payload.file_size_bytes,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def claim(self) -> ClaimedJobRecord | None:
        now = datetime.now(UTC)
        stmt = (
            select(EtlJob)
            .where(EtlJob.status == JobStatus.PENDING)
            .where(EtlJob.attempt_count < EtlJob.max_attempts)
            .where(EtlJob.file_path.is_not(None))
            .where(
                or_(
                    EtlJob.processing_started_at.is_(None),
                    EtlJob.processing_started_at <= now,
                )
            )
            .order_by(EtlJob.file_size_bytes.asc().nulls_last(), EtlJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        async with QueueSession.transaction(self.db):
            result = await self.db.execute(stmt)
            job = result.scalar_one_or_none()
            if job is None:
                return None

            job.status = JobStatus.PROCESSING
            job.attempt_count += 1
            job.claimed_at = now
            job.processing_started_at = now
            job.last_heartbeat_at = now
            job.last_error = None
            await self.db.flush()

            return self._to_claimed(job)

    async def ack(self, job_id: str) -> None:
        job = await self._get_job(UUID(job_id))
        if job is None:
            return
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.claimed_at = None
        job.last_heartbeat_at = datetime.now(UTC)

    async def fail(
        self,
        job_id: str,
        *,
        error_message: str,
        attempt_count: int,
        max_attempts: int,
        poison: bool = False,
        retry_reason: RetryReason | str = RetryReason.GENERIC,
    ) -> None:
        job = await self._get_job(UUID(job_id))
        if job is None:
            return
        reason = RetryReason(retry_reason) if isinstance(retry_reason, str) else retry_reason
        job.last_error = error_message
        retry_eligible_at: datetime | None = None
        if poison or attempt_count >= max_attempts:
            job.status = JobStatus.DEAD_LETTER
            job.claimed_at = None
            job.processing_started_at = None
        elif attempt_count < max_attempts:
            job.status = JobStatus.PENDING
            job.claimed_at = None
            retry_eligible_at = compute_etl_retry_eligible_at(attempt_count)
            job.processing_started_at = retry_eligible_at
            _queue_logger.warning(
                "etl_job_requeued_with_backoff",
                extra=retry_audit_extra(
                    job_id=job_id,
                    attempt_count=attempt_count,
                    max_attempts=max_attempts,
                    retry_reason=reason,
                    retry_eligible_at=retry_eligible_at,
                    error_message=error_message,
                ),
            )
        else:
            job.status = JobStatus.FAILED
            job.claimed_at = None
            job.processing_started_at = None

    async def requeue(self, job_id: str) -> None:
        job = await self._get_job(UUID(job_id))
        if job is None:
            return
        if job.status not in (JobStatus.FAILED, JobStatus.DEAD_LETTER):
            return
        if job.attempt_count >= job.max_attempts:
            return
        job.status = JobStatus.PENDING
        job.claimed_at = None
        job.processing_started_at = None
        job.last_error = "Manually requeued"

    async def recover_stale(self) -> list[RecoveryRecord]:
        now = datetime.now(UTC)
        stmt = (
            select(EtlJob)
            .where(EtlJob.status == JobStatus.PROCESSING)
            .where(EtlJob.claimed_at.is_not(None))
            .with_for_update(skip_locked=True)
        )

        recovered: list[RecoveryRecord] = []
        async with QueueSession.transaction(self.db):
            result = await self.db.execute(stmt)
            for job in result.scalars().all():
                if job.claimed_at is None:
                    continue
                if not is_etl_job_stale(job, now):
                    continue

                if job.attempt_count < job.max_attempts:
                    job.status = JobStatus.PENDING
                    job.claimed_at = None
                    job.last_error = "Visibility timeout expired; job requeued"
                    job.processing_started_at = compute_etl_retry_eligible_at(job.attempt_count)
                    _queue_logger.warning(
                        "etl_job_requeued_with_backoff",
                        extra=retry_audit_extra(
                            job_id=str(job.id),
                            attempt_count=job.attempt_count,
                            max_attempts=job.max_attempts,
                            retry_reason=RetryReason.VISIBILITY_TIMEOUT,
                            retry_eligible_at=job.processing_started_at,
                            error_message=job.last_error,
                        ),
                    )
                else:
                    job.status = JobStatus.DEAD_LETTER
                    job.last_error = "Max attempts exceeded after visibility timeout"

                recovered.append(
                    RecoveryRecord(
                        job_id=job.id,
                        report_id=job.report_id,
                        user_id=job.user_id,
                        new_status=job.status.value,
                        last_error=job.last_error,
                    )
                )
        return recovered

    async def heartbeat(self, job_id: str) -> None:
        job = await self._get_job(UUID(job_id))
        if job is None or job.status != JobStatus.PROCESSING:
            return
        job.last_heartbeat_at = datetime.now(UTC)

    async def _get_job(self, job_id: UUID) -> EtlJob | None:
        result = await self.db.execute(select(EtlJob).where(EtlJob.id == job_id))
        return result.scalar_one_or_none()

    @staticmethod
    def _to_claimed(job: EtlJob) -> ClaimedJobRecord:
        return ClaimedJobRecord(
            job_id=job.id,
            report_id=job.report_id,
            user_id=job.user_id,
            report_created_at=job.report_created_at,
            marketplace=job.marketplace,
            report_type=job.report_type,
            original_filename=job.original_filename,
            file_path=job.file_path or "",
            attempt_count=job.attempt_count,
            max_attempts=job.max_attempts,
            idempotency_key=job.idempotency_key,
            visibility_timeout_seconds=job.visibility_timeout_seconds,
        )

"""Explicit, idempotent tenant recovery primitives (operator/worker invoked)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import get_logger
from app.core.queue import get_queue_backend
from app.core.queue.stale import is_etl_job_stale
from app.core.security_context import QueueSession, TenantSession
from app.models.inventory.staging import WarehouseStockSnapshotStaging
from app.models.job import EtlJob, JobStatus
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.operations.rebuild_orchestration import compute_next_eligible_at

logger = get_logger("tenant_recovery")


@dataclass(frozen=True)
class RecoveryActionResult:
    action: str
    affected_count: int
    detail: str
    job_ids: tuple[str, ...] = ()


class TenantRecoveryService:
    """
    Survivability helpers — must be called explicitly; no background auto-retry loops.

    All mutations are tenant-scoped via RLS (TenantSession) or filtered queue recovery.
    """

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def reset_stale_running_rebuilds(
        self,
        *,
        stale_after_seconds: int = 3600,
    ) -> RecoveryActionResult:
        """Crash mid-rebuild: orchestration stuck in RUNNING → DEFERRED with backoff."""
        cutoff = datetime.now(UTC) - timedelta(seconds=stale_after_seconds)
        async with TenantSession.transaction(self.db, self.user_id):
            result = await self.db.execute(
                select(SnapshotRebuildRequirement).where(
                    SnapshotRebuildRequirement.user_id == self.user_id,
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.RUNNING,
                    SnapshotRebuildRequirement.started_at.is_not(None),
                    SnapshotRebuildRequirement.started_at < cutoff,
                )
            )
            rows = list(result.scalars().all())
            for row in rows:
                row.orchestration_status = RebuildOrchestrationStatus.DEFERRED
                row.last_error = "stale RUNNING reset by recovery"
                row.next_eligible_at = compute_next_eligible_at(row.attempt_count)
            count = len(rows)
        if count:
            logger.warning(
                "recovery_stale_running_rebuilds",
                extra={
                    "user_id": str(self.user_id),
                    "affected_count": count,
                    "stale_after_seconds": stale_after_seconds,
                },
            )
        return RecoveryActionResult(
            action="reset_stale_running_rebuilds",
            affected_count=count,
            detail=f"reset {count} stale RUNNING rebuild requirement(s)",
        )

    async def cleanup_orphaned_staging(
        self,
        *,
        older_than_seconds: int = 86_400,
    ) -> RecoveryActionResult:
        """Remove aged staging rows after crashed promote (live snapshots unchanged)."""
        cutoff = datetime.now(UTC) - timedelta(seconds=older_than_seconds)
        async with TenantSession.transaction(self.db, self.user_id):
            count_before = (
                await self.db.execute(
                    select(func.count())
                    .select_from(WarehouseStockSnapshotStaging)
                    .where(WarehouseStockSnapshotStaging.user_id == self.user_id)
                )
            ).scalar_one()
            await self.db.execute(
                delete(WarehouseStockSnapshotStaging).where(
                    WarehouseStockSnapshotStaging.user_id == self.user_id,
                    WarehouseStockSnapshotStaging.created_at < cutoff,
                )
            )
            count_after = (
                await self.db.execute(
                    select(func.count())
                    .select_from(WarehouseStockSnapshotStaging)
                    .where(WarehouseStockSnapshotStaging.user_id == self.user_id)
                )
            ).scalar_one()
        removed = int(count_before) - int(count_after)
        if removed:
            logger.warning(
                "recovery_orphaned_staging_cleanup",
                extra={
                    "user_id": str(self.user_id),
                    "removed_rows": removed,
                    "older_than_seconds": older_than_seconds,
                },
            )
        return RecoveryActionResult(
            action="cleanup_orphaned_staging",
            affected_count=removed,
            detail=f"removed {removed} staging row(s) older than {older_than_seconds}s",
        )

    async def recover_stuck_processing_jobs(self) -> RecoveryActionResult:
        """Tenant-filtered visibility recovery (same rules as global recover_stale)."""
        now = datetime.now(UTC)
        recovered_ids: list[str] = []
        async with QueueSession.transaction(self.db):
            result = await self.db.execute(
                select(EtlJob)
                .where(
                    EtlJob.user_id == self.user_id,
                    EtlJob.status == JobStatus.PROCESSING,
                    EtlJob.claimed_at.is_not(None),
                )
                .with_for_update(skip_locked=True)
            )
            for job in result.scalars().all():
                if job.claimed_at is None:
                    continue
                if not is_etl_job_stale(job, now):
                    continue
                if job.attempt_count < job.max_attempts:
                    job.status = JobStatus.PENDING
                    job.claimed_at = None
                    job.processing_started_at = None
                    job.last_error = "Visibility timeout expired; tenant recovery requeued"
                else:
                    job.status = JobStatus.DEAD_LETTER
                    job.last_error = "Max attempts exceeded after visibility timeout"
                recovered_ids.append(str(job.id))

        if recovered_ids:
            logger.warning(
                "recovery_stuck_processing_jobs",
                extra={
                    "user_id": str(self.user_id),
                    "job_ids": recovered_ids,
                    "affected_count": len(recovered_ids),
                },
            )
        return RecoveryActionResult(
            action="recover_stuck_processing_jobs",
            affected_count=len(recovered_ids),
            detail=f"recovered {len(recovered_ids)} stuck PROCESSING job(s)",
            job_ids=tuple(recovered_ids),
        )

    async def replay_dead_letter_job(
        self,
        job_id: UUID,
        *,
        reset_attempt_counter: bool = False,
    ) -> RecoveryActionResult:
        """
        Explicit dead-letter replay — does not run ETL; only requeues for worker.

        reset_attempt_counter: operator acknowledges counter reset (logged).
        """
        async with TenantSession.transaction(self.db, self.user_id):
            job = await self.db.get(EtlJob, job_id)
            if job is None or job.user_id != self.user_id:
                return RecoveryActionResult(
                    action="replay_dead_letter_job",
                    affected_count=0,
                    detail="job not found for tenant",
                )
            if job.status != JobStatus.DEAD_LETTER:
                return RecoveryActionResult(
                    action="replay_dead_letter_job",
                    affected_count=0,
                    detail=f"job status is {job.status.value}, not dead_letter",
                )
            if reset_attempt_counter:
                job.attempt_count = 0

        async with QueueSession.transaction(self.db):
            await get_queue_backend(self.db).requeue(str(job_id))

        async with TenantSession.transaction(self.db, self.user_id):
            job = await self.db.get(EtlJob, job_id)
            if job is None or job.status != JobStatus.PENDING:
                return RecoveryActionResult(
                    action="replay_dead_letter_job",
                    affected_count=0,
                    detail="requeue rejected (attempt_count >= max_attempts?)",
                )

        logger.warning(
            "recovery_dead_letter_replay",
            extra={
                "user_id": str(self.user_id),
                "job_id": str(job_id),
                "reset_attempt_counter": reset_attempt_counter,
            },
        )
        from app.runtime.audit.operator import record_operator_action

        await record_operator_action(
            self.db,
            action_type="replay_dead_letter_job",
            detail=f"replayed job {job_id}",
            user_id=self.user_id,
            actor_type="recovery_service",
            payload={
                "job_id": str(job_id),
                "reset_attempt_counter": reset_attempt_counter,
            },
        )
        return RecoveryActionResult(
            action="replay_dead_letter_job",
            affected_count=1,
            detail="job moved to PENDING for worker pickup",
            job_ids=(str(job_id),),
        )

    async def apply_rebuild_retry_backoff(self) -> RecoveryActionResult:
        """Ensure DEFERRED/FAILED rows have explicit next_eligible_at (idempotent)."""
        async with TenantSession.transaction(self.db, self.user_id):
            result = await self.db.execute(
                select(SnapshotRebuildRequirement).where(
                    SnapshotRebuildRequirement.user_id == self.user_id,
                    SnapshotRebuildRequirement.requires_rebuild.is_(True),
                    SnapshotRebuildRequirement.orchestration_status.in_(
                        (
                            RebuildOrchestrationStatus.DEFERRED,
                            RebuildOrchestrationStatus.FAILED,
                            RebuildOrchestrationStatus.PENDING,
                        )
                    ),
                    SnapshotRebuildRequirement.attempt_count
                    < SnapshotRebuildRequirement.max_attempts,
                )
            )
            updated = 0
            for row in result.scalars().all():
                if row.next_eligible_at is None and row.attempt_count < row.max_attempts:
                    row.next_eligible_at = compute_next_eligible_at(row.attempt_count)
                    if row.orchestration_status == RebuildOrchestrationStatus.FAILED:
                        row.orchestration_status = RebuildOrchestrationStatus.DEFERRED
                    updated += 1
        if updated:
            logger.info(
                "recovery_rebuild_backoff_applied",
                extra={"user_id": str(self.user_id), "affected_count": updated},
            )
        return RecoveryActionResult(
            action="apply_rebuild_retry_backoff",
            affected_count=updated,
            detail=f"scheduled backoff on {updated} rebuild requirement(s)",
        )

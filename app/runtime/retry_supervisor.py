"""Retry supervision for orchestration and queue hygiene (explicit, bounded)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import DispatchSession
from app.models.job import EtlJob, JobStatus
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.operations.rebuild_orchestration import compute_next_eligible_at
from app.operations.recovery import TenantRecoveryService
from app.runtime.metrics import emit_runtime_metric


@dataclass(frozen=True)
class RetrySupervisorReport:
    stale_running_reset: int
    backoff_rows_updated: int
    poison_orchestration_rows: int
    tenants_recovery_jobs: int


class RetrySupervisor:
    """
    Maintenance pass — idempotent, no infinite loops.

    Invoked on a bounded schedule from the orchestration worker.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run_maintenance(self) -> RetrySupervisorReport:
        stale_reset = await self._reset_stale_running_globally()
        backoff_updated = await self._apply_missing_backoff()
        poison_count = await self._flag_poison_orchestration()
        recovery_jobs = await self._recover_stale_processing_sample()
        report = RetrySupervisorReport(
            stale_running_reset=stale_reset,
            backoff_rows_updated=backoff_updated,
            poison_orchestration_rows=poison_count,
            tenants_recovery_jobs=recovery_jobs,
        )
        emit_runtime_metric(
            "runtime_retry_supervisor_completed",
            stale_running_reset=report.stale_running_reset,
            backoff_rows_updated=report.backoff_rows_updated,
            poison_orchestration_rows=report.poison_orchestration_rows,
            tenants_recovery_jobs=report.tenants_recovery_jobs,
        )
        return report

    async def _reset_stale_running_globally(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.recovery_stale_running_seconds)
        tenant_ids = await self._distinct_tenants_with_stale_running(cutoff)
        total = 0
        for user_id in tenant_ids:
            result = await TenantRecoveryService(self.db, user_id).reset_stale_running_rebuilds(
                stale_after_seconds=settings.recovery_stale_running_seconds,
            )
            total += result.affected_count
        return total

    async def _distinct_tenants_with_stale_running(self, cutoff: datetime) -> list:
        from uuid import UUID

        async with DispatchSession.transaction(self.db):
            rows = (
                await self.db.execute(
                    select(SnapshotRebuildRequirement.user_id)
                    .where(
                        SnapshotRebuildRequirement.orchestration_status
                        == RebuildOrchestrationStatus.RUNNING,
                        SnapshotRebuildRequirement.started_at.is_not(None),
                        SnapshotRebuildRequirement.started_at < cutoff,
                    )
                    .distinct()
                )
            ).all()
        return [UUID(str(r[0])) for r in rows]

    async def _apply_missing_backoff(self) -> int:
        from uuid import UUID

        async with DispatchSession.transaction(self.db):
            tenant_rows = (
                await self.db.execute(
                    select(SnapshotRebuildRequirement.user_id)
                    .where(
                        SnapshotRebuildRequirement.requires_rebuild.is_(True),
                        SnapshotRebuildRequirement.orchestration_status.in_(
                            (
                                RebuildOrchestrationStatus.DEFERRED,
                                RebuildOrchestrationStatus.FAILED,
                                RebuildOrchestrationStatus.PENDING,
                            )
                        ),
                        SnapshotRebuildRequirement.next_eligible_at.is_(None),
                        SnapshotRebuildRequirement.attempt_count
                        < SnapshotRebuildRequirement.max_attempts,
                    )
                    .distinct()
                )
            ).all()
        updated = 0
        for (user_id_raw,) in tenant_rows:
            user_id = UUID(str(user_id_raw))
            result = await TenantRecoveryService(self.db, user_id).apply_rebuild_retry_backoff()
            updated += result.affected_count
        return updated

    async def _flag_poison_orchestration(self) -> int:
        """Log orchestration rows that repeated the same terminal error (audit visibility)."""
        async with DispatchSession.transaction(self.db):
            rows = (
                await self.db.execute(
                    select(SnapshotRebuildRequirement)
                    .where(
                        SnapshotRebuildRequirement.orchestration_status
                        == RebuildOrchestrationStatus.FAILED,
                        SnapshotRebuildRequirement.attempt_count
                        >= SnapshotRebuildRequirement.max_attempts,
                    )
                    .limit(50)
                )
            ).scalars().all()
        for row in rows:
            emit_runtime_metric(
                "runtime_orchestration_poison",
                user_id=str(row.user_id),
                requirement_id=str(row.id),
                last_error=row.last_error,
                attempt_count=row.attempt_count,
            )
        return len(rows)

    async def _recover_stale_processing_sample(self) -> int:
        from uuid import UUID

        async with DispatchSession.transaction(self.db):
            tenant_rows = (
                await self.db.execute(
                    select(EtlJob.user_id)
                    .where(EtlJob.status == JobStatus.PROCESSING)
                    .distinct()
                    .limit(20)
                )
            ).all()
        recovered = 0
        for (user_id_raw,) in tenant_rows:
            user_id = UUID(str(user_id_raw))
            result = await TenantRecoveryService(self.db, user_id).recover_stuck_processing_jobs()
            recovered += result.affected_count
        return recovered

    @staticmethod
    def orchestration_retry_budget_remaining(row: SnapshotRebuildRequirement) -> int:
        return max(0, row.max_attempts - row.attempt_count)

    @staticmethod
    def schedule_next_orchestration_retry(row: SnapshotRebuildRequirement) -> datetime:
        return compute_next_eligible_at(row.attempt_count)

"""Bounded self-healing — explicit, logged, tenant-scoped."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.core.security_context import DispatchSession, TenantSession
from app.models.job import EtlJob, JobStatus
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.operations.rebuild_orchestration import RebuildOrchestrationService
from app.operations.recovery import TenantRecoveryService
from app.runtime.autonomy.audit import record_autonomy_event
from app.runtime.policy.engine import RuntimeOperationalPolicy
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AutonomyAction:
    action_type: str
    affected_count: int
    detail: str
    user_id: UUID | None = None


class AutonomousHealer:
    """Runs only when policy.autonomy_enabled; capped actions per cycle."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: RuntimeOperationalPolicy | None = None,
    ) -> None:
        self.db = db
        self.policy = policy or RuntimeOperationalPolicy.from_settings()

    async def run_bounded_cycle(self) -> list[AutonomyAction]:
        if not self.policy.autonomy_enabled:
            return []
        actions: list[AutonomyAction] = []
        cap = self.policy.max_autonomous_actions_per_cycle

        stale = await self._reset_stale_rebuilds()
        if stale.affected_count:
            actions.append(stale)
        if len(actions) >= cap:
            return actions[:cap]

        throttle = await self._defer_overloaded_tenants()
        if throttle.affected_count:
            actions.append(throttle)
        if len(actions) >= cap:
            return actions[:cap]

        jobs = await self._recover_stuck_jobs_sample()
        if jobs.affected_count:
            actions.append(jobs)

        return actions[:cap]

    async def _reset_stale_rebuilds(self) -> AutonomyAction:
        from app.runtime.retry_supervisor import RetrySupervisor

        report = await RetrySupervisor(self.db).run_maintenance()
        count = report.stale_running_reset
        if count:
            await record_autonomy_event(
                self.db,
                action_type="auto_reset_stale_rebuilds",
                detail=f"reset {count} stale RUNNING rebuild(s)",
                reversible=True,
                payload={"count": count},
            )
        return AutonomyAction(
            action_type="auto_reset_stale_rebuilds",
            affected_count=count,
            detail=f"stale_running_reset={count}",
        )

    async def _defer_overloaded_tenants(self) -> AutonomyAction:
        threshold = max(10, self.policy.queue_overload_threshold // 2)
        async with DispatchSession.transaction(self.db):
            tenant_rows = (
                await self.db.execute(
                    select(EtlJob.user_id, func.count())
                    .where(EtlJob.status == JobStatus.PENDING)
                    .group_by(EtlJob.user_id)
                    .having(func.count() >= threshold)
                )
            ).all()
        deferred = 0
        for user_id, pending_count in tenant_rows:
            async with TenantSession.transaction(self.db, user_id):
                rows = (
                    await self.db.execute(
                        select(SnapshotRebuildRequirement)
                        .where(
                            SnapshotRebuildRequirement.user_id == user_id,
                            SnapshotRebuildRequirement.requires_rebuild.is_(True),
                            SnapshotRebuildRequirement.orchestration_status.in_(
                                (
                                    RebuildOrchestrationStatus.PENDING,
                                    RebuildOrchestrationStatus.QUEUED,
                                )
                            ),
                        )
                        .limit(2)
                    )
                ).scalars().all()
                orch = RebuildOrchestrationService(self.db, user_id)
                for row in rows:
                    await orch.mark_deferred_lock_busy(
                        row,
                        defer_seconds=settings.orchestrator_defer_busy_seconds * 2,
                    )
                    deferred += 1
            if deferred:
                await record_autonomy_event(
                    self.db,
                    action_type="auto_defer_overloaded_tenant",
                    user_id=user_id,
                    detail=f"deferred rebuilds under queue pressure (pending={pending_count})",
                    reversible=True,
                )
        return AutonomyAction(
            action_type="auto_defer_overloaded_tenant",
            affected_count=deferred,
            detail=f"deferred={deferred}",
        )

    async def _recover_stuck_jobs_sample(self) -> AutonomyAction:
        async with DispatchSession.transaction(self.db):
            tenants = (
                await self.db.execute(
                    select(EtlJob.user_id)
                    .where(EtlJob.status == JobStatus.PROCESSING)
                    .distinct()
                    .limit(5)
                )
            ).all()
        total = 0
        for (user_id,) in tenants:
            result = await TenantRecoveryService(self.db, user_id).recover_stuck_processing_jobs()
            total += result.affected_count
            if result.affected_count:
                await record_autonomy_event(
                    self.db,
                    action_type="auto_recover_stuck_jobs",
                    user_id=user_id,
                    detail=result.detail,
                    reversible=True,
                    payload={"job_ids": list(result.job_ids)},
                )
        return AutonomyAction(
            action_type="auto_recover_stuck_jobs",
            affected_count=total,
            detail=f"recovered={total}",
        )

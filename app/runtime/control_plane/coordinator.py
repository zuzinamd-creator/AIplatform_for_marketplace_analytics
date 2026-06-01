"""Runtime control plane coordinator — ties health, schedules, dispatch policy."""

from __future__ import annotations

from dataclasses import dataclass

from app.runtime.control_plane.state import (
    ControlPlaneSnapshot,
    RuntimeHealthSeverity,
    TenantOperationalState,
    WorkloadState,
)
from app.runtime.health.evaluator import PlatformHealthReport, RuntimeHealthEvaluator
from app.runtime.metrics import emit_runtime_metric
from app.runtime.observability import collect_global_queue_metrics, collect_rebuild_queue_metrics
from app.runtime.policy.engine import RuntimeOperationalPolicy
from app.runtime.reliability.degradation import assess_platform_degradation
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches
from app.runtime.runtime_guards import RuntimeGuardState, check_queue_overload
from app.runtime.scheduling.executor import ScheduleExecutor
from app.runtime.scheduling.registry import ScheduleKind, ScheduleRegistry
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ControlPlaneCycleResult:
    dispatched_rebuild: bool
    health: PlatformHealthReport
    schedules_run: tuple[str, ...]
    snapshot: ControlPlaneSnapshot


class RuntimeControlPlane:
    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: RuntimeOperationalPolicy | None = None,
        guard_state: RuntimeGuardState | None = None,
        schedule_registry: ScheduleRegistry | None = None,
    ) -> None:
        self.db = db
        self.policy = policy or RuntimeOperationalPolicy.from_settings()
        self.guard_state = guard_state or RuntimeGuardState()
        self.schedules = schedule_registry or ScheduleRegistry.default()
        self._executor = ScheduleExecutor(db, policy=self.policy, guard_state=self.guard_state)
        self._health = RuntimeHealthEvaluator()

    async def run_cycle(self) -> ControlPlaneCycleResult:
        from app.runtime.rebuild_dispatcher import RebuildDispatcher

        schedules_run: list[str] = []
        for kind in self.schedules.due_kinds():
            if kind == ScheduleKind.REBUILD_DISPATCH:
                continue
            report = await self._executor.run(kind)
            schedules_run.append(f"{kind.value}:{report.detail}")
            self.schedules.advance(kind)

        queue = await collect_global_queue_metrics(self.db)
        rebuild = await collect_rebuild_queue_metrics(self.db)
        check_queue_overload(
            pending_jobs=queue.pending_count,
            threshold=self.policy.queue_overload_threshold,
        )
        health = self._health.evaluate(queue=queue, rebuild=rebuild)
        degradation = assess_platform_degradation(health=health, queue_pending=queue.pending_count)
        emit_runtime_metric(
            "runtime_degradation_state",
            level=degradation.level.value,
            reason=degradation.reason,
        )

        dispatched = False
        dispatch_switch = RuntimeKillSwitches.check(KillSwitchDomain.REBUILD_DISPATCH)
        if (
            dispatch_switch.allowed
            and not self.policy.should_throttle_dispatch(
                queue_pending=queue.pending_count,
                rebuild_backlog=rebuild.pending_dispatch + rebuild.deferred,
            )
        ):
            result = await RebuildDispatcher(self.db, guard_state=self.guard_state).dispatch_once()
            dispatched = result.dispatched
            schedules_run.append(f"dispatch:{result.outcome}")
        elif not dispatch_switch.allowed:
            schedules_run.append(f"dispatch:blocked:{dispatch_switch.reason}")

        snapshot = self.snapshot_from_metrics(queue, rebuild, health)
        return ControlPlaneCycleResult(
            dispatched_rebuild=dispatched,
            health=health,
            schedules_run=tuple(schedules_run),
            snapshot=snapshot,
        )

    def snapshot_from_metrics(
        self,
        queue,
        rebuild,
        health: PlatformHealthReport,
    ) -> ControlPlaneSnapshot:
        tenant_state = TenantOperationalState.HEALTHY
        if health.overall_severity == RuntimeHealthSeverity.CRITICAL:
            tenant_state = TenantOperationalState.OVERLOADED
        elif health.overall_severity == RuntimeHealthSeverity.WARN:
            tenant_state = TenantOperationalState.DEGRADED
        if rebuild.pending_dispatch + rebuild.deferred > self.policy.dispatch_batch_size * 5:
            tenant_state = TenantOperationalState.REBUILD_PRESSURE

        workload = WorkloadState.IDLE
        if self.policy.should_throttle_dispatch(
            queue_pending=queue.pending_count,
            rebuild_backlog=rebuild.pending_dispatch,
        ):
            workload = WorkloadState.THROTTLED

        return ControlPlaneSnapshot(
            tenant_state=tenant_state,
            workload_state=workload,
            health_score=health.overall_score,
            health_severity=health.overall_severity,
            queue_pending=queue.pending_count,
            rebuild_backlog=rebuild.pending_dispatch + rebuild.deferred,
            rebuild_running=rebuild.running,
            recommendations=health.recommendations,
        )

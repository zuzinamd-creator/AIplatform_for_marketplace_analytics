"""Execute due schedules (explicit handlers, auditable)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.autonomy.healer import AutonomousHealer
from app.runtime.health.evaluator import RuntimeHealthEvaluator
from app.runtime.metrics import emit_runtime_metric
from app.runtime.observability import collect_global_queue_metrics, collect_rebuild_queue_metrics
from app.runtime.policy.engine import RuntimeOperationalPolicy
from app.runtime.retry_supervisor import RetrySupervisor
from app.runtime.runtime_guards import RuntimeGuardState
from app.runtime.scheduling.registry import ScheduleKind


@dataclass(frozen=True)
class ScheduleExecutionReport:
    kind: ScheduleKind
    detail: str


class ScheduleExecutor:
    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: RuntimeOperationalPolicy | None = None,
        guard_state: RuntimeGuardState | None = None,
    ) -> None:
        self.db = db
        self.policy = policy or RuntimeOperationalPolicy.from_settings()
        self.guard_state = guard_state or RuntimeGuardState()
        self._health = RuntimeHealthEvaluator()

    async def run(self, kind: ScheduleKind) -> ScheduleExecutionReport:
        if kind == ScheduleKind.ORCHESTRATION_MAINTENANCE:
            report = await RetrySupervisor(self.db).run_maintenance()
            return ScheduleExecutionReport(
                kind=kind,
                detail=(
                    f"stale_reset={report.stale_running_reset} "
                    f"backoff={report.backoff_rows_updated}"
                ),
            )
        if kind == ScheduleKind.AUTONOMY_HEALING:
            if not self.policy.autonomy_enabled:
                return ScheduleExecutionReport(kind=kind, detail="autonomy disabled")
            actions = await AutonomousHealer(self.db, policy=self.policy).run_bounded_cycle()
            return ScheduleExecutionReport(kind=kind, detail=f"actions={len(actions)}")
        if kind == ScheduleKind.HEALTH_EVALUATION:
            queue = await collect_global_queue_metrics(self.db)
            rebuild = await collect_rebuild_queue_metrics(self.db)
            health = self._health.evaluate(queue=queue, rebuild=rebuild)
            emit_runtime_metric(
                "runtime_health_evaluated",
                overall_score=health.overall_score,
                severity=health.overall_severity.value,
            )
            return ScheduleExecutionReport(
                kind=kind,
                detail=f"score={health.overall_score} severity={health.overall_severity.value}",
            )
        if kind == ScheduleKind.QUEUE_VISIBILITY:
            await collect_global_queue_metrics(self.db)
            await collect_rebuild_queue_metrics(self.db)
            return ScheduleExecutionReport(kind=kind, detail="metrics collected")
        if kind == ScheduleKind.ENTERPRISE_OPERATIONS:
            from app.runtime.enterprise.coordinator import AutonomousOperationsEngine

            if not self.policy.autonomy_enabled:
                return ScheduleExecutionReport(kind=kind, detail="enterprise ops skipped: autonomy disabled")
            result = await AutonomousOperationsEngine(self.db, policy=self.policy).run_cycle(dry_run=False)
            return ScheduleExecutionReport(
                kind=kind,
                detail=(
                    f"executed={result.remediation.executed_steps} "
                    f"blocked={result.remediation.blocked_steps}"
                ),
            )
        if kind == ScheduleKind.OPERATIONAL_FORECAST:
            from app.runtime.enterprise.coordinator import AutonomousOperationsEngine

            result = await AutonomousOperationsEngine(self.db, policy=self.policy).run_cycle(dry_run=True)
            return ScheduleExecutionReport(
                kind=kind,
                detail=f"overload_risk={result.forecast.overload_risk}",
            )
        if kind == ScheduleKind.DLQ_SWEEP:
            queue = await collect_global_queue_metrics(self.db)
            return ScheduleExecutionReport(
                kind=kind, detail=f"dlq_visible count={queue.dead_letter_count}"
            )
        return ScheduleExecutionReport(kind=kind, detail="no-op")

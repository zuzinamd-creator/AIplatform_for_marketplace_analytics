"""Autonomous operations engine — enterprise cycle coordinator."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.runtime.enterprise.audit import record_autonomous_action
from app.runtime.enterprise.decision_engine import OperationalDecisionEngine
from app.runtime.enterprise.dto import EnterpriseOpsCycleResult
from app.runtime.enterprise.forecasting import RuntimeIntelligenceEngine
from app.runtime.enterprise.remediation import GovernedRemediationExecutor, RemediationPlanner
from app.runtime.enterprise.scheduling import EnterpriseScheduleRegistry
from app.runtime.enterprise.strategy import RuntimeStrategyLayer
from app.runtime.health.evaluator import RuntimeHealthEvaluator
from app.runtime.metrics import emit_runtime_metric
from app.runtime.observability import collect_global_queue_metrics, collect_rebuild_queue_metrics
from app.runtime.policy.engine import RuntimeOperationalPolicy


class AutonomousOperationsEngine:
    """Semi-autonomous enterprise operations cycle (policy-governed, auditable)."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: RuntimeOperationalPolicy | None = None,
    ) -> None:
        self.db = db
        self.policy = policy or RuntimeOperationalPolicy.from_settings()
        self._forecast = RuntimeIntelligenceEngine()
        self._decisions = OperationalDecisionEngine()
        self._planner = RemediationPlanner()
        self._executor = GovernedRemediationExecutor(db, policy=self.policy)
        self._strategy = RuntimeStrategyLayer()
        self._health = RuntimeHealthEvaluator()

    async def run_cycle(self, *, dry_run: bool = False) -> EnterpriseOpsCycleResult:
        if not getattr(settings, "runtime_enterprise_ops_enabled", True):
            queue = await collect_global_queue_metrics(self.db)
            rebuild = await collect_rebuild_queue_metrics(self.db)
            health = self._health.evaluate(queue=queue, rebuild=rebuild)
            forecast = self._forecast.forecast(
                queue=queue, rebuild=rebuild, health=health, policy=self.policy
            )
            plan = self._planner.build_plan([])
            remediation = await self._executor.execute(plan, dry_run=True)
            return EnterpriseOpsCycleResult(
                forecast=forecast, plan=plan, remediation=remediation, journal_ids=[]
            )

        queue = await collect_global_queue_metrics(self.db)
        rebuild = await collect_rebuild_queue_metrics(self.db)
        health = self._health.evaluate(queue=queue, rebuild=rebuild)
        forecast = self._forecast.forecast(
            queue=queue, rebuild=rebuild, health=health, policy=self.policy
        )
        strategy = self._strategy.advise(
            forecast=forecast, queue=queue, rebuild=rebuild, policy=self.policy
        )
        in_blackout = await EnterpriseScheduleRegistry.platform_in_blackout(self.db)
        decisions = self._decisions.decide(
            forecast=forecast,
            queue=queue,
            rebuild=rebuild,
            policy=self.policy,
            in_blackout=in_blackout or strategy.throttle_dispatch,
        )
        plan = self._planner.build_plan(decisions)
        remediation = await self._executor.execute(plan, dry_run=dry_run)

        correlation_id = str(uuid4())[:16]
        journal_ids = []
        for decision in plan.decisions:
            if decision.kind.value == "no_action":
                continue
            row = await record_autonomous_action(
                self.db,
                user_id=None,
                decision=decision,
                plan=plan,
                result=remediation,
                dry_run=dry_run,
                correlation_id=correlation_id,
            )
            journal_ids.append(row.id)

        emit_runtime_metric(
            "enterprise_ops_cycle",
            dry_run=dry_run,
            executed=remediation.executed_steps,
            blocked=remediation.blocked_steps,
            overload_risk=str(forecast.overload_risk),
        )
        return EnterpriseOpsCycleResult(
            forecast=forecast,
            plan=plan,
            remediation=remediation,
            journal_ids=journal_ids,
        )

"""Remediation planner and governed executor."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.autonomy.healer import AutonomousHealer
from app.runtime.enterprise.dto import (
    OperationalDecisionDTO,
    OperationalDecisionKind,
    RemediationPlanDTO,
    RemediationResultDTO,
    RemediationStepDTO,
)
from app.runtime.enterprise.governance import AutonomyPermissionMatrix
from app.runtime.policy.engine import RuntimeOperationalPolicy


class RemediationPlanner:
    def build_plan(self, decisions: list[OperationalDecisionDTO]) -> RemediationPlanDTO:
        steps: list[RemediationStepDTO] = []
        for decision in decisions:
            if decision.kind == OperationalDecisionKind.NO_ACTION:
                continue
            steps.append(
                RemediationStepDTO(
                    step_id=decision.decision_id[:8],
                    action_type=decision.kind.value,
                    reversible=decision.reversible,
                    detail=decision.rationale,
                )
            )
        return RemediationPlanDTO(
            plan_id=str(uuid4()),
            decisions=tuple(decisions),
            steps=tuple(steps),
            dependency_notes="Steps ordered by priority; capped by policy per cycle.",
        )


class GovernedRemediationExecutor:
    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: RuntimeOperationalPolicy | None = None,
    ) -> None:
        self.db = db
        self.policy = policy or RuntimeOperationalPolicy.from_settings()
        self._healer = AutonomousHealer(db, policy=self.policy)

    async def execute(
        self,
        plan: RemediationPlanDTO,
        *,
        dry_run: bool,
    ) -> RemediationResultDTO:
        executed = 0
        blocked = 0
        details: list[str] = []

        for step in plan.steps[: self.policy.max_autonomous_actions_per_cycle]:
            kind = OperationalDecisionKind(step.action_type)
            perm = AutonomyPermissionMatrix.evaluate(kind, dry_run=dry_run)
            if not perm.allowed:
                blocked += 1
                details.append(f"blocked:{step.action_type}")
                continue
            if perm.requires_approval and not dry_run:
                blocked += 1
                details.append(f"approval_required:{step.action_type}")
                continue
            if dry_run:
                executed += 1
                details.append(f"simulated:{step.action_type}")
                continue
            if kind in (
                OperationalDecisionKind.RESET_STALE_REBUILD,
                OperationalDecisionKind.DEFER_REBUILD,
                OperationalDecisionKind.HEAL_QUEUE,
                OperationalDecisionKind.RECOVER_STUCK_JOBS,
            ):
                actions = await self._healer.run_bounded_cycle()
                executed += len(actions)
                details.append(f"healer:{len(actions)}")
            elif kind == OperationalDecisionKind.THROTTLE_DISPATCH:
                executed += 1
                details.append("throttle:policy_active")

        return RemediationResultDTO(
            plan_id=plan.plan_id,
            dry_run=dry_run,
            executed_steps=executed,
            blocked_steps=blocked,
            detail="; ".join(details) or "no-op",
        )

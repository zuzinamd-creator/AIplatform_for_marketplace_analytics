"""Autonomous action journal persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import DispatchSession
from app.models.enterprise_runtime import AutonomousActionStatus, RuntimeAutonomousAction
from app.runtime.enterprise.dto import (
    OperationalDecisionDTO,
    RemediationPlanDTO,
    RemediationResultDTO,
)
from app.runtime.metrics import emit_runtime_metric


async def record_autonomous_action(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    decision: OperationalDecisionDTO,
    plan: RemediationPlanDTO,
    result: RemediationResultDTO,
    dry_run: bool,
    correlation_id: str | None = None,
) -> RuntimeAutonomousAction:
    status = AutonomousActionStatus.SIMULATED if dry_run else AutonomousActionStatus.EXECUTED
    if result.blocked_steps > 0 and result.executed_steps == 0:
        status = AutonomousActionStatus.BLOCKED

    row = RuntimeAutonomousAction(
        user_id=user_id,
        decision_id=decision.decision_id,
        action_type=decision.kind.value,
        status=status,
        dry_run=dry_run,
        reversible=decision.reversible,
        detail=result.detail[:4000],
        provenance={
            "rationale": decision.rationale,
            "plan_id": plan.plan_id,
            "requires_approval": decision.requires_approval,
        },
        lineage={"plan_steps": [s.step_id for s in plan.steps]},
        payload={"executed": result.executed_steps, "blocked": result.blocked_steps},
        correlation_id=correlation_id,
    )
    async with DispatchSession.transaction(db):
        db.add(row)
        await db.flush()
    emit_runtime_metric(
        "runtime_autonomous_action",
        action_type=decision.kind.value,
        status=status.value,
        dry_run=dry_run,
    )
    return row

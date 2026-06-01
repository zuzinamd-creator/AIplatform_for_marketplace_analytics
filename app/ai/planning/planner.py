"""Action plan builder — multi-step advisory workflows."""

from __future__ import annotations

from uuid import uuid4

from app.dto.ai_analytics_dto import AnalyticsWorkflow
from app.dto.ai_intelligence_dto import ActionPlanDTO, AgentRole, PlanStepDTO


def build_action_plan(workflow: AnalyticsWorkflow) -> ActionPlanDTO:
    plan_id = str(uuid4())
    steps: list[PlanStepDTO] = [
        PlanStepDTO(
            step_id="gather_context",
            agent_role=AgentRole.PLANNER,
            description="Assemble grounded analytics context and semantics version",
        ),
        PlanStepDTO(
            step_id="analyze",
            agent_role=AgentRole.ANALYST,
            description=f"Run {workflow.value} analysis on grounded metrics",
            depends_on=("gather_context",),
        ),
        PlanStepDTO(
            step_id="validate",
            agent_role=AgentRole.VALIDATOR,
            description="Verify numeric sanity, contradictions, unsupported claims",
            depends_on=("analyze",),
        ),
        PlanStepDTO(
            step_id="ops_review",
            agent_role=AgentRole.OPERATIONS_ADVISOR,
            description="Simulate operational impact (read-only; no mutations)",
            depends_on=("validate",),
            simulated=True,
        ),
    ]
    return ActionPlanDTO(
        plan_id=plan_id,
        workflow=workflow,
        steps=tuple(steps),
        dependency_notes="All steps are advisory; execution simulation only",
    )

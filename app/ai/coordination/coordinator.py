"""Multi-agent coordination — governed inter-agent communication."""

from __future__ import annotations

from uuid import UUID

from app.ai.decision.engine import AIDecisionEngine
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import AgentMessageDTO, AgentRole, IntelligenceRunResultDTO


class MultiAgentCoordinator:
    """Planner → Analyst → Validator → Operations Advisor pipeline (advisory-only)."""

    def __init__(self) -> None:
        self._decision = AIDecisionEngine()

    def coordinate(
        self,
        *,
        run_id: UUID,
        validated: ValidatedInsightDTO,
        grounded: GroundedContextDTO,
        insight_id: UUID | None = None,
    ) -> IntelligenceRunResultDTO:
        from app.ai.explainability.builder import build_explainability
        from app.ai.planning.planner import build_action_plan
        from app.ai.validation.recommendation_validator import validate_recommendation

        messages: list[AgentMessageDTO] = []
        plan = build_action_plan(validated.workflow)
        messages.append(
            AgentMessageDTO(
                from_role=AgentRole.PLANNER,
                to_role=AgentRole.ANALYST,
                message_type="plan_ready",
                payload_summary=f"plan {plan.plan_id} with {len(plan.steps)} steps",
            )
        )

        scored = self._decision.score_recommendation(validated=validated, grounded=grounded)
        messages.append(
            AgentMessageDTO(
                from_role=AgentRole.ANALYST,
                to_role=AgentRole.VALIDATOR,
                message_type="analysis_complete",
                payload_summary=f"confidence={scored.confidence} priority={scored.priority_score}",
            )
        )

        validation = validate_recommendation(scored=scored, grounded=grounded)
        scored = scored.model_copy(
            update={
                "unsupported_claims": validation.unsupported_claims,
                "contradictions": validation.contradictions,
            }
        )
        messages.append(
            AgentMessageDTO(
                from_role=AgentRole.VALIDATOR,
                to_role=AgentRole.OPERATIONS_ADVISOR,
                message_type="validation_complete",
                payload_summary=f"valid={validation.is_valid} issues={len(validation.contradictions)}",
            )
        )

        if grounded.rebuild_pending_count > 0 or grounded.degraded_mode:
            messages.append(
                AgentMessageDTO(
                    from_role=AgentRole.OPERATIONS_ADVISOR,
                    to_role=AgentRole.COORDINATOR,
                    message_type="ops_context",
                    payload_summary="degraded runtime context noted for operator",
                )
            )

        explain = build_explainability(
            validated=validated,
            grounded=grounded,
            scored=scored,
            agent_messages=tuple(messages),
        )

        return IntelligenceRunResultDTO(
            run_id=run_id,
            recommendation=scored,
            action_plan=plan,
            explainability=explain,
            agent_messages=tuple(messages),
            grounded=grounded,
            insight_id=insight_id,
        )

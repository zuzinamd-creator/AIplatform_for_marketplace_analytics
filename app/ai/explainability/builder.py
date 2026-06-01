"""Explainability builder — evidence graph and operator summaries."""

from __future__ import annotations

from decimal import Decimal

from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import (
    AgentMessageDTO,
    AgentRole,
    EvidenceGraphDTO,
    EvidenceNodeDTO,
    ExplainabilityDTO,
    ReasoningStepDTO,
    ScoredRecommendationDTO,
)


def build_explainability(
    *,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    scored: ScoredRecommendationDTO,
    agent_messages: tuple[AgentMessageDTO, ...],
) -> ExplainabilityDTO:
    nodes: list[EvidenceNodeDTO] = []
    edges: list[tuple[str, str, str]] = []
    for idx, ref in enumerate(grounded.evidence):
        node_id = f"ev_{idx}"
        nodes.append(
            EvidenceNodeDTO(
                node_id=node_id,
                label=ref.label,
                source_type=ref.source_type,
                source_id=ref.source_id,
                supports_claim=validated.summary[:120],
            )
        )
        edges.append((node_id, "claim_primary", "supports"))

    trace: list[ReasoningStepDTO] = [
        ReasoningStepDTO(
            agent_role=AgentRole.ANALYST,
            step="grounded_analysis",
            detail=f"Semantics {grounded.semantics_version}; evidence count {len(grounded.evidence)}",
            confidence_contribution=Decimal("0.4"),
        ),
        ReasoningStepDTO(
            agent_role=AgentRole.VALIDATOR,
            step="claim_verification",
            detail=f"Unsupported: {len(scored.unsupported_claims)}; contradictions: {len(scored.contradictions)}",
            confidence_contribution=Decimal("0.3"),
        ),
    ]

    freshness = Decimal("1.0")
    if validated.stale_data_warning:
        freshness = Decimal("0.5")
    elif grounded.degraded_mode:
        freshness = Decimal("0.7")

    rationale = (
        f"Confidence {scored.confidence} adjusted for evidence, stale context, and validation."
    )
    if scored.requires_human_approval:
        rationale += f" Requires human approval ({scored.approval_category})."

    return ExplainabilityDTO(
        summary_for_operator=validated.summary[:2000],
        confidence_rationale=rationale,
        evidence_graph=EvidenceGraphDTO(nodes=tuple(nodes), edges=tuple(edges)),
        reasoning_trace=tuple(trace),
        provenance={
            "workflow": validated.workflow.value,
            "semantics_version": validated.semantics_version,
            "agent_messages": str(len(agent_messages)),
        },
        freshness_score=freshness,
    )

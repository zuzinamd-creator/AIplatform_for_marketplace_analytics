"""Multi-layer intelligence pipeline — domain analysts + executive aggregation."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts import build_analytical_package, run_domain_analysts
from app.ai.executive import ExecutiveIntelligenceAggregator
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import (
    AgentMessageDTO,
    AgentRole,
    EvidenceGraphDTO,
    EvidenceNodeDTO,
    ExplainabilityDTO,
    IntelligenceRunResultDTO,
    ReasoningStepDTO,
)
from app.dto.analytics_dto import AIInsightInputDTO
from app.dto.domain_analyst_dto import MultiLayerReasoningTraceDTO


def run_multi_layer_pipeline(
    *,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    insight_input: AIInsightInputDTO | None,
) -> MultiLayerReasoningTraceDTO:
    package = build_analytical_package(grounded=grounded, insight=insight_input)
    domain_outputs = run_domain_analysts(package)
    executive = ExecutiveIntelligenceAggregator().aggregate(domain_outputs)
    return MultiLayerReasoningTraceDTO(
        domain_outputs=domain_outputs,
        executive=executive,
        conflict_resolution=executive.conflicts_resolved,
        confidence_propagation=executive.confidence_propagation,
        domain_insights=executive.prioritized_insights,
    )


def enrich_intelligence_result(
    result: IntelligenceRunResultDTO,
    *,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    insight_input: AIInsightInputDTO | None,
    multi_trace: MultiLayerReasoningTraceDTO | None = None,
) -> IntelligenceRunResultDTO:
    """Apply multi-layer reasoning on top of coordinator output (advisory-only)."""
    trace = multi_trace or run_multi_layer_pipeline(
        validated=validated,
        grounded=grounded,
        insight_input=insight_input,
    )
    executive = trace.executive
    if executive is None:
        return result

    rec = result.recommendation
    bullets = list(rec.bullets)
    for action in executive.final_recommendations[:5]:
        if action not in bullets:
            bullets.append(action)

    merged_confidence = min(
        Decimal("1"),
        (rec.confidence + executive.overall_confidence) / Decimal("2"),
    )
    if executive.prioritized_insights:
        top = executive.prioritized_insights[0]
        priority_boost = min(Decimal("100"), rec.priority_score + top.business_impact_score / Decimal("4"))
    else:
        priority_boost = rec.priority_score

    updated_rec = rec.model_copy(
        update={
            "summary": executive.executive_summary or rec.summary,
            "bullets": bullets[:12],
            "confidence": merged_confidence,
            "priority_score": priority_boost,
        }
    )

    explain = _build_multi_layer_explainability(
        base=result.explainability,
        trace=trace,
        validated=validated,
    )

    messages = list(result.agent_messages)
    messages.append(
        AgentMessageDTO(
            from_role=AgentRole.COORDINATOR,
            to_role=AgentRole.ANALYST,
            message_type="multi_layer_complete",
            payload_summary=(
                f"domain_analysts=6 insights={len(trace.domain_insights)} "
                f"conflicts={len(trace.conflict_resolution)}"
            ),
        )
    )

    return result.model_copy(
        update={
            "recommendation": updated_rec,
            "explainability": explain,
            "agent_messages": tuple(messages),
        },
    )


def _build_multi_layer_explainability(
    *,
    base: ExplainabilityDTO,
    trace: MultiLayerReasoningTraceDTO,
    validated: ValidatedInsightDTO,
) -> ExplainabilityDTO:
    nodes = list(base.evidence_graph.nodes)
    edges = list(base.evidence_graph.edges)
    for ins in trace.domain_insights[:12]:
        node_id = f"ml_{ins.insight_id[:40]}"
        nodes.append(
            EvidenceNodeDTO(
                node_id=node_id,
                label=f"{ins.analyst_label}: {ins.statement[:80]}",
                source_type="domain_analyst",
                source_id=ins.analyst_id,
                supports_claim=ins.statement[:120],
            )
        )
        edges.append((node_id, "executive_priority", f"rank_{ins.priority_rank}"))

    steps = list(base.reasoning_trace)
    steps.append(
        ReasoningStepDTO(
            agent_role=AgentRole.ANALYST,
            step="multi_layer_domain_analysis",
            detail=f"Six domain analysts produced {len(trace.domain_outputs)} structured outputs",
            confidence_contribution=Decimal("0.2"),
        )
    )
    if trace.executive:
        steps.append(
            ReasoningStepDTO(
                agent_role=AgentRole.COORDINATOR,
                step="executive_aggregation",
                detail=trace.executive.business_impact_estimate,
                confidence_contribution=Decimal("0.15"),
            )
        )

    rationale = base.confidence_rationale + " Multi-layer v2 confidence propagation applied."
    return ExplainabilityDTO(
        summary_for_operator=trace.executive.narrative[:2000] if trace.executive else base.summary_for_operator,
        confidence_rationale=rationale,
        evidence_graph=EvidenceGraphDTO(nodes=tuple(nodes), edges=tuple(edges)),
        reasoning_trace=tuple(steps),
        provenance={
            **base.provenance,
            "architecture": "multi_layer_v2",
            "domain_analyst_count": "6",
        },
        freshness_score=base.freshness_score,
    )


def reasoning_trace_payload(
    result: IntelligenceRunResultDTO,
    trace: MultiLayerReasoningTraceDTO,
) -> dict:
    return {
        "steps": [s.model_dump(mode="json") for s in result.explainability.reasoning_trace],
        "agent_messages": [m.model_dump(mode="json") for m in result.agent_messages],
        "multi_layer": trace.model_dump(mode="json"),
        "domain_insights": [i.model_dump(mode="json") for i in trace.domain_insights],
    }

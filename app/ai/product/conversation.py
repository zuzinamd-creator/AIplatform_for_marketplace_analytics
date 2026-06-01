"""Deterministic conversational explanations — no autonomous agent actions."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.ai_intelligence import AIRecommendation


@dataclass(frozen=True)
class ConversationReplyDTO:
    question: str
    answer: str
    sources: list[str]
    advisory_only: bool = True


def answer_follow_up(rec: AIRecommendation, *, question: str) -> ConversationReplyDTO:
    """Map seller questions to stored trace / action_plan (explainable, bounded)."""
    q = question.strip().lower()
    plan = rec.action_plan or {}
    trace = rec.reasoning_trace or {}
    usefulness = plan.get("seller_usefulness") or {}
    domain_insights = trace.get("domain_insights") or []

    if q in ("why", "why?", "why this", "why does this matter"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("why_this_matters")
                or plan.get("why_this_matters")
                or rec.summary
            )[:2000],
            sources=["action_plan.seller_usefulness", "summary"],
        )

    if q in ("impact", "business impact", "what impact"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("expected_business_impact")
                or plan.get("impact_estimate")
                or "Impact estimate not stored for this recommendation."
            )[:1500],
            sources=["seller_usefulness.expected_business_impact"],
        )

    if q in ("action", "what should i do", "next step", "what action"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("concrete_next_action")
                or plan.get("recommended_action")
                or "Review evidence, then apply changes in your marketplace seller account."
            )[:1500],
            sources=["seller_usefulness.concrete_next_action"],
        )

    if q in ("confidence", "how confident", "why confidence"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("confidence_explanation")
                or f"Stored confidence {rec.confidence_score}; risk class {rec.risk_class.value}."
            )[:1500],
            sources=["confidence_score", "seller_usefulness.confidence_explanation"],
        )

    if q in ("evidence", "proof", "what evidence"):
        graph = rec.evidence_graph or {}
        nodes = graph.get("nodes") or []
        if not nodes:
            return ConversationReplyDTO(
                question=question,
                answer="No evidence nodes attached. Upload reports and re-run intelligence when rebuilds are healthy.",
                sources=["evidence_graph"],
            )
        lines = [f"- {n.get('label', 'ref')}: {n.get('source_type')}/{n.get('source_id')}" for n in nodes[:8]]
        return ConversationReplyDTO(
            question=question,
            answer="Evidence references:\n" + "\n".join(lines),
            sources=["evidence_graph.nodes"],
        )

    if q.startswith("analyst") or "domain" in q:
        if not domain_insights:
            return ConversationReplyDTO(
                question=question,
                answer="No domain analyst breakdown on this recommendation (pre–REAL-AI-2 or empty package).",
                sources=["reasoning_trace.domain_insights"],
            )
        top = domain_insights[0]
        return ConversationReplyDTO(
            question=question,
            answer=(
                f"Top domain insight from {top.get('analyst_label', 'analyst')}: "
                f"{top.get('statement', '')}"
            )[:2000],
            sources=["reasoning_trace.domain_insights"],
        )

    if "limitation" in q or "can ai" in q:
        lim = usefulness.get("limitations") or [
            "Advisory only; does not execute marketplace changes.",
        ]
        return ConversationReplyDTO(
            question=question,
            answer="\n".join(f"- {x}" for x in lim[:6]),
            sources=["seller_usefulness.limitations"],
        )

    return ConversationReplyDTO(
        question=question,
        answer=(
            "Try: why · impact · action · confidence · evidence · analyst · limitations. "
            "Answers are generated from stored recommendation data, not autonomous decisions."
        ),
        sources=["conversation.help"],
    )

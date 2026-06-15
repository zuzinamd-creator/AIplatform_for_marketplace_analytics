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

    if q in ("why", "why?", "why this", "why does this matter", "почему"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("why_this_matters")
                or plan.get("why_this_matters")
                or rec.summary
            )[:2000],
            sources=["action_plan.seller_usefulness", "summary"],
        )

    if q in ("impact", "business impact", "what impact", "эффект"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("expected_business_impact")
                or plan.get("impact_estimate")
                or "Оценка эффекта для этой рекомендации не сохранена."
            )[:1500],
            sources=["seller_usefulness.expected_business_impact"],
        )

    if q in ("action", "what should i do", "next step", "what action", "действие"):
        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("concrete_next_action")
                or plan.get("recommended_action")
                or "Сверьте KPI на Dashboard и примените изменения в кабинете маркетплейса."
            )[:1500],
            sources=["seller_usefulness.concrete_next_action"],
        )

    if q in ("confidence", "how confident", "why confidence", "уверенность"):
        from app.ai.presentation.seller_display import confidence_label_ru, risk_label_ru

        return ConversationReplyDTO(
            question=question,
            answer=str(
                usefulness.get("confidence_explanation")
                or f"Уверенность: {confidence_label_ru(rec.confidence_score)}; риск: {risk_label_ru(rec.risk_class.value)}."
            )[:1500],
            sources=["confidence_score", "seller_usefulness.confidence_explanation"],
        )

    if q in ("evidence", "proof", "what evidence", "доказательства"):
        graph = rec.evidence_graph or {}
        nodes = graph.get("nodes") or []
        if not nodes:
            return ConversationReplyDTO(
                question=question,
                answer="Доказательства не приложены. Загрузите отчёты и повторите анализ.",
                sources=["evidence_graph"],
            )
        lines = [f"- {n.get('label', 'источник')}" for n in nodes[:8]]
        return ConversationReplyDTO(
            question=question,
            answer="Источники данных:\n" + "\n".join(lines),
            sources=["evidence_graph.nodes"],
        )

    if q.startswith("analyst") or "domain" in q:
        if not domain_insights:
            return ConversationReplyDTO(
                question=question,
                answer="Для этой рекомендации нет разбивки по бизнес-областям.",
                sources=["reasoning_trace.domain_insights"],
            )
        from app.ai.presentation.seller_display import sanitize_domain_insight_for_seller

        top = sanitize_domain_insight_for_seller(domain_insights[0])
        return ConversationReplyDTO(
            question=question,
            answer=(
                f"Главный сигнал ({top.get('domain', 'данные')}): "
                f"{top.get('statement', '')}"
            )[:2000],
            sources=["reasoning_trace.domain_insights"],
        )

    if "limitation" in q or "can ai" in q or "ограничен" in q:
        lim = usefulness.get("limitations") or [
            "Рекомендация носит advisory-характер и не меняет карточки автоматически.",
        ]
        return ConversationReplyDTO(
            question=question,
            answer="\n".join(f"- {x}" for x in lim[:6]),
            sources=["seller_usefulness.limitations"],
        )

    return ConversationReplyDTO(
        question=question,
        answer=(
            "Спросите: «почему», «эффект», «действие», «уверенность», «доказательства», «ограничения». "
            "Ответы формируются из сохранённых данных рекомендации."
        ),
        sources=["conversation.help"],
    )

"""Seller intelligence package — actionable recommendations + today's focus."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.product.impact_estimation import build_measurable_impact
from app.ai.product.prioritization import (
    PRIORITY_INFORMATIONAL,
    PRIORITY_TODAY,
    compute_seller_priority,
)
from app.ai.product.seller_usefulness import build_seller_usefulness
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO
from app.models.ai_intelligence import AIRecommendation, SellerWorkflowState


@dataclass(frozen=True)
class ActionableRecommendationDTO:
    recommendation_id: str
    title: str
    summary: str
    seller_usefulness: dict
    recommendation_score: float
    priority_tier: str
    priority_score: float | None


@dataclass(frozen=True)
class TodaysFocusDTO:
    generated_at: datetime
    headline: str
    requires_attention_today: list[str]
    can_wait: list[str]
    dangerous: list[str]
    highest_upside: list[str]
    top_actions: list[dict]
    critical_alerts: list[dict]
    quick_wins: list[dict]
    priority_queue: list[ActionableRecommendationDTO]
    advisory_notice: str


def build_actionable_payload(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    flags: list[str],
    fatigue_penalty: float = 0.0,
    novelty_score: float = 1.0,
) -> dict:
    """Full seller-oriented action plan fields for persistence."""
    evidence_refs = [f"{e.source_type}:{e.source_id}" for e in grounded.evidence[:10]]
    usefulness = build_seller_usefulness(
        scored=scored, validated=validated, grounded=grounded, flags=flags
    )
    impact = build_measurable_impact(
        scored=scored,
        validated=validated,
        grounded=grounded,
        evidence_refs=evidence_refs,
    )
    priority = compute_seller_priority(
        scored=scored,
        validated=validated,
        grounded=grounded,
        urgency_score=usefulness.urgency_score,
        novelty_score=novelty_score,
        fatigue_penalty=fatigue_penalty,
    )

    wf = validated.workflow.value
    root_cause = _root_cause(wf, flags, validated)
    what_changed = _what_changed(grounded, validated)
    what_today = usefulness.concrete_next_action if priority.priority_tier == PRIORITY_TODAY else (
        "Review in today's focus queue — no immediate marketplace change required."
    )
    effort = "15–30 min" if priority.priority_tier == PRIORITY_TODAY else "30–60 min this week"
    if wf == "anomaly_explanation":
        effort = "30–45 min (data fix before other actions)"

    return {
        "why_this_matters": usefulness.why_this_matters,
        "expected_business_impact": usefulness.expected_business_impact,
        "urgency": usefulness.urgency,
        "urgency_score": usefulness.urgency_score,
        "root_cause": root_cause,
        "what_changed": what_changed,
        "what_to_do_today": what_today,
        "recommended_action": usefulness.concrete_next_action,
        "estimated_effort": effort,
        "expected_outcome": usefulness.estimated_upside,
        "estimated_upside": usefulness.estimated_upside,
        "estimated_downside": usefulness.estimated_downside,
        "confidence_explanation": usefulness.confidence_explanation,
        "limitations": usefulness.limitations,
        "measurable_impact": {
            "summary": impact.summary,
            "estimates": [
                {
                    "category": e.category,
                    "range_label": e.range_label,
                    "confidence_band": e.confidence_band,
                    "evidence_refs": e.evidence_refs,
                    "uncertainty_note": e.uncertainty_note,
                }
                for e in impact.estimates
            ],
            "do_not_trust_exact_amounts": True,
        },
        "prioritization": {
            "recommendation_score": float(priority.recommendation_score),
            "priority_tier": priority.priority_tier,
            "today_priority": priority.today_priority,
            "score_breakdown": priority.score_breakdown,
        },
        "novelty_score": novelty_score,
        "fatigue_penalty": fatigue_penalty,
    }


def _root_cause(workflow: str, flags: list[str], validated: ValidatedInsightDTO) -> str:
    if workflow == "anomaly_explanation":
        return "Report or ETL data quality issue affecting KPI reliability."
    if "stale_or_degraded_context" in flags:
        return "Analytics snapshot may be outdated (rebuild or pending refresh)."
    if validated.unsupported_claims:
        return "Model output included claims not fully supported by governed metrics."
    if workflow == "inventory_insight":
        return "SKU or stock signals in governed package suggest inventory attention."
    return "Shift in governed revenue, margin, or catalog metrics vs prior period."


def _what_changed(grounded: GroundedContextDTO, validated: ValidatedInsightDTO) -> str:
    parts = [f"Workflow: {validated.workflow.value}"]
    if grounded.freshness_note:
        parts.append(f"Freshness: {grounded.freshness_note}")
    rev = grounded.metrics_snapshot.get("total_revenue")
    if rev is not None:
        parts.append(f"Governed total_revenue present ({rev}).")
    return " ".join(parts)


class TodaysFocusService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def build(self) -> TodaysFocusDTO:
        async with TenantSession.transaction(self.db, self.user_id):
            rows = (
                await self.db.execute(
                    select(AIRecommendation)
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(
                        AIRecommendation.seller_workflow_state.in_(
                            (SellerWorkflowState.ACTIVE.value, SellerWorkflowState.SAVED.value)
                        )
                    )
                    .order_by(AIRecommendation.priority_score.desc().nullslast())
                    .limit(30)
                )
            ).scalars().all()

        items: list[ActionableRecommendationDTO] = []
        for r in rows:
            plan = r.action_plan or {}
            su = plan.get("seller_usefulness") or plan
            pri = su.get("prioritization") or plan.get("prioritization") or {}
            tier = str(pri.get("priority_tier", PRIORITY_INFORMATIONAL))
            items.append(
                ActionableRecommendationDTO(
                    recommendation_id=str(r.id),
                    title=r.title,
                    summary=r.summary[:300],
                    seller_usefulness=su if isinstance(su, dict) else {},
                    recommendation_score=float(pri.get("recommendation_score", r.priority_score or 0)),
                    priority_tier=tier,
                    priority_score=float(r.priority_score) if r.priority_score else None,
                )
            )

        items.sort(key=lambda x: x.recommendation_score, reverse=True)
        today_items = [i for i in items if i.priority_tier == PRIORITY_TODAY]
        week_items = [i for i in items if i.priority_tier == "this_week"]
        info_items = [i for i in items if i.priority_tier == PRIORITY_INFORMATIONAL]

        dangerous = [
            i.title for i in today_items
            if (i.seller_usefulness.get("urgency_score") or 0) >= 80
            or "anomaly" in i.summary.lower()
        ][:5]
        upside = sorted(today_items + week_items, key=lambda x: x.recommendation_score, reverse=True)[:3]
        top_actions = [
            {
                "recommendation_id": i.recommendation_id,
                "action": i.seller_usefulness.get("what_to_do_today")
                or i.seller_usefulness.get("recommended_action")
                or "Review detail",
                "tier": i.priority_tier,
            }
            for i in (today_items[:3] or items[:3])
        ]
        critical = [
            {"title": i.title, "tier": i.priority_tier, "why": i.seller_usefulness.get("why_this_matters", "")[:200]}
            for i in today_items
            if (i.seller_usefulness.get("urgency_score") or 0) >= 75
        ][:5]
        quick_wins = [
            {
                "title": i.title,
                "action": i.seller_usefulness.get("recommended_action", "")[:200],
                "effort": i.seller_usefulness.get("estimated_effort", "low"),
            }
            for i in week_items
            if (i.seller_usefulness.get("estimated_effort") or "").startswith("15")
        ][:3]

        headline = (
            f"Today's focus: {len(today_items)} urgent, {len(week_items)} this week, "
            f"{len(info_items)} informational"
            if items
            else "No active recommendations — upload reports and run intelligence."
        )

        return TodaysFocusDTO(
            generated_at=datetime.now(UTC),
            headline=headline,
            requires_attention_today=[i.title for i in today_items[:5]],
            can_wait=[i.title for i in week_items[:5]] + [i.title for i in info_items[:3]],
            dangerous=dangerous,
            highest_upside=[i.title for i in upside],
            top_actions=top_actions,
            critical_alerts=critical,
            quick_wins=quick_wins,
            priority_queue=items[:15],
            advisory_notice=(
                "Today's Focus is advisory. Verify evidence before marketplace changes. "
                "Impact figures are ranges, not guarantees."
            ),
        )

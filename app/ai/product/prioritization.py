"""Seller recommendation prioritization — today / this week / informational."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO

PRIORITY_TODAY = "today"
PRIORITY_THIS_WEEK = "this_week"
PRIORITY_INFORMATIONAL = "informational"


@dataclass(frozen=True)
class SellerPriorityResult:
    recommendation_score: Decimal
    priority_tier: str
    today_priority: bool
    score_breakdown: dict[str, float]


def compute_seller_priority(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    urgency_score: int,
    novelty_score: float = 1.0,
    fatigue_penalty: float = 0.0,
) -> SellerPriorityResult:
    """Deterministic seller-oriented priority (not generic LLM priority)."""
    revenue = float(scored.revenue_opportunity_score)
    confidence = float(scored.confidence)
    priority_base = float(scored.priority_score)

    # Trust / deterioration signals from governed context (never from raw reports).
    anomalies = grounded.metrics_snapshot.get("anomalies") if isinstance(grounded.metrics_snapshot, dict) else None
    anomaly_text = ""
    if isinstance(anomalies, list) and anomalies:
        anomaly_text = " ".join(str(a.get("message", "")) for a in anomalies if isinstance(a, dict)).lower()

    anomaly_boost = 0.0
    if validated.workflow.value in ("anomaly_explanation", "risk_detection"):
        anomaly_boost = 22.0
    if grounded.degraded_mode or validated.stale_data_warning:
        anomaly_boost += 8.0

    inventory_boost = 0.0
    if validated.workflow.value == "inventory_insight":
        inventory_boost = 12.0

    confidence_penalty = 0.0
    if "низкая уверенность" in anomaly_text or "себестоимость" in anomaly_text and "отсутств" in anomaly_text:
        # Missing/partial costs -> avoid "do today" unless the action is to fix costs.
        confidence_penalty += 12.0
    if "расхождение выплат" in anomaly_text or "payout" in anomaly_text:
        confidence_penalty += 6.0

    urgency_factor = urgency_score * 0.35
    score = (
        priority_base * 0.35
        + revenue * 0.2
        + confidence * 40.0
        + urgency_factor
        + anomaly_boost
        + inventory_boost
        + novelty_score * 10.0
        - fatigue_penalty
        - confidence_penalty
    )
    score = max(0.0, min(100.0, score))

    tier = PRIORITY_INFORMATIONAL
    if score >= 72 or urgency_score >= 80:
        tier = PRIORITY_TODAY
    elif score >= 48 or urgency_score >= 55:
        tier = PRIORITY_THIS_WEEK

    breakdown = {
        "priority_base": priority_base,
        "revenue_opportunity": revenue,
        "confidence": confidence,
        "urgency_score": float(urgency_score),
        "anomaly_boost": anomaly_boost,
        "novelty": novelty_score,
        "fatigue_penalty": fatigue_penalty,
        "confidence_penalty": confidence_penalty,
    }

    return SellerPriorityResult(
        recommendation_score=Decimal(str(round(score, 2))),
        priority_tier=tier,
        today_priority=tier == PRIORITY_TODAY,
        score_breakdown=breakdown,
    )

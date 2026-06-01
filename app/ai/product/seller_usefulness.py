"""Seller-facing usefulness enrichment (deterministic, non-LLM filler)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


@dataclass(frozen=True)
class SellerUsefulnessDTO:
    why_this_matters: str
    expected_business_impact: str
    urgency: str
    urgency_score: int
    estimated_upside: str
    estimated_downside: str
    concrete_next_action: str
    confidence_explanation: str
    limitations: list[str]


def build_seller_usefulness(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    flags: list[str],
) -> SellerUsefulnessDTO:
    limitations: list[str] = [
        "Advisory only — does not change prices, ads, or inventory in your marketplace account.",
        "KPIs come from your uploaded reports and deterministic analytics, not from live marketplace APIs.",
    ]

    urgency_score = 50
    if validated.workflow.value in ("risk_detection", "anomaly_explanation"):
        urgency_score = 85
    elif scored.priority_score >= Decimal("70"):
        urgency_score = 75
    elif scored.priority_score >= Decimal("40"):
        urgency_score = 55
    else:
        urgency_score = 35

    if "stale_or_degraded_context" in flags:
        urgency_score = min(urgency_score, 45)
        limitations.append("Data may be stale or rebuild is in progress — verify KPIs before acting.")

    if "no_evidence" in flags:
        limitations.append("Limited evidence references attached to this recommendation.")

    urgency = "this_week"
    if urgency_score >= 80:
        urgency = "today"
    elif urgency_score >= 60:
        urgency = "this_week"
    else:
        urgency = "when_convenient"

    why = (
        "This insight connects governed KPIs to a specific operational decision "
        "(revenue, margin, inventory risk, or data quality)."
    )
    if validated.workflow.value == "anomaly_explanation":
        why = "Data-quality issues can distort revenue and margin KPIs until resolved."
    elif scored.revenue_opportunity_score >= Decimal("40"):
        why = "Revenue or margin signals suggest a near-term profit opportunity if you act on evidence."

    impact = "moderate operational or profit impact if validated"
    if urgency_score >= 80:
        impact = "high — address before trusting week-over-week comparisons"
    elif urgency_score < 45:
        impact = "low — informational; verify when convenient"

    upside = "Protect margin or recover revenue after evidence check"
    downside = "Delayed action may leave incorrect listings, costs, or campaigns unchanged"
    if "stale_or_degraded_context" in flags:
        downside = "Acting on stale KPIs may cause wrong pricing or stock decisions"

    action = scored.bullets[0] if scored.bullets else (
        "Open evidence → confirm numbers in analytics → apply change in marketplace seller cabinet → mark completed here."
    )

    conf_parts = [f"Model confidence {scored.confidence:.0%} after validation."]
    if flags:
        conf_parts.append(f"Adjusted for: {', '.join(flags)}.")
    if grounded.degraded_mode:
        conf_parts.append("Degraded runtime context reduced confidence.")
    if validated.stale_data_warning:
        conf_parts.append("Stale data warning active.")

    return SellerUsefulnessDTO(
        why_this_matters=why,
        expected_business_impact=impact,
        urgency=urgency,
        urgency_score=urgency_score,
        estimated_upside=upside,
        estimated_downside=downside,
        concrete_next_action=action[:500],
        confidence_explanation=" ".join(conf_parts),
        limitations=limitations,
    )

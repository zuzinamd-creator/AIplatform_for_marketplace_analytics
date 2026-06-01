"""Recommendation governance — approval gates and trust model."""

from __future__ import annotations

from dataclasses import dataclass

from app.dto.ai_intelligence_dto import RiskClassification, ScoredRecommendationDTO


@dataclass(frozen=True)
class GatedRecommendation:
    recommendation: ScoredRecommendationDTO
    requires_human_approval: bool
    risk_class: RiskClassification
    approval_category: str | None
    trust_level: str


def classify_and_gate(scored: ScoredRecommendationDTO) -> GatedRecommendation:
    risk = scored.risk_class
    requires = scored.requires_human_approval
    category = scored.approval_category

    if scored.contradictions:
        risk = RiskClassification.HIGH
        requires = True
        category = category or "contradiction_detected"

    if scored.unsupported_claims and _risk_rank(risk) < _risk_rank(RiskClassification.MEDIUM):
        risk = RiskClassification.MEDIUM

    trust = "high" if scored.confidence >= 0.75 and not requires else "medium"
    if _risk_rank(risk) >= _risk_rank(RiskClassification.HIGH):
        trust = "low"

    updated = scored.model_copy(
        update={
            "risk_class": risk,
            "requires_human_approval": requires,
            "approval_category": category,
        }
    )
    return GatedRecommendation(
        recommendation=updated,
        requires_human_approval=requires,
        risk_class=risk,
        approval_category=category,
        trust_level=trust,
    )


def _risk_rank(risk: RiskClassification) -> int:
    return {
        RiskClassification.LOW: 0,
        RiskClassification.MEDIUM: 1,
        RiskClassification.HIGH: 2,
        RiskClassification.CRITICAL: 3,
    }[risk]

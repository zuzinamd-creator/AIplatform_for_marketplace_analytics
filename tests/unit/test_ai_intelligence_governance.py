"""Unit tests for recommendation governance gates."""

from __future__ import annotations

from decimal import Decimal

from app.ai.governance.recommendation_policy import classify_and_gate
from app.dto.ai_intelligence_dto import RiskClassification, ScoredRecommendationDTO


def test_contradictions_force_approval() -> None:
    scored = ScoredRecommendationDTO(
        title="Test",
        summary="Summary",
        confidence=Decimal("0.9"),
        priority_score=Decimal("50"),
        requires_human_approval=False,
        contradictions=["high confidence without evidence refs"],
    )
    gated = classify_and_gate(scored)
    assert gated.requires_human_approval is True
    assert gated.risk_class == RiskClassification.HIGH
    assert gated.trust_level == "low"

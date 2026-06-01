"""Recommendation validation — sanity, contradictions, stale context."""

from __future__ import annotations

from dataclasses import dataclass

from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


@dataclass(frozen=True)
class RecommendationValidationResult:
    is_valid: bool
    unsupported_claims: list[str]
    contradictions: list[str]
    stale_context: bool


def validate_recommendation(
    *,
    scored: ScoredRecommendationDTO,
    grounded: GroundedContextDTO,
) -> RecommendationValidationResult:
    unsupported = list(scored.unsupported_claims)
    contradictions: list[str] = []

    revenue = grounded.metrics_snapshot.get("total_revenue")
    if revenue is not None:
        try:
            if float(revenue) < 0 and "growth" in scored.summary.lower():
                contradictions.append("claims growth while revenue metric is negative")
        except (TypeError, ValueError):
            pass

    if scored.confidence > 0.8 and not grounded.evidence:
        contradictions.append("high confidence without evidence refs")

    stale = grounded.degraded_mode or grounded.rebuild_running_count > 0
    if stale and "immediate action" in scored.summary.lower():
        contradictions.append("urgency language under stale/degraded context")

    is_valid = not contradictions and not unsupported
    return RecommendationValidationResult(
        is_valid=is_valid,
        unsupported_claims=unsupported,
        contradictions=contradictions,
        stale_context=stale,
    )

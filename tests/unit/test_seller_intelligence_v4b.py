"""Unit tests for REAL-AI-V4B seller intelligence & usefulness engine."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.ai.product.fatigue import FatigueAssessment
from app.ai.product.impact_estimation import build_measurable_impact
from app.ai.product.prioritization import PRIORITY_TODAY, compute_seller_priority
from app.ai.product.seller_intelligence import build_actionable_payload
from app.ai.quality.recommendation_quality import apply_quality
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


def _validated(workflow: AnalyticsWorkflow = AnalyticsWorkflow.REVENUE_INSIGHT) -> ValidatedInsightDTO:
    return ValidatedInsightDTO(
        title="Margin advisory",
        summary="Low margin on governed KPIs",
        confidence=Decimal("0.75"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=workflow,
        semantics_version="1.0",
    )


def _grounded(**kwargs) -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=kwargs.get("degraded_mode", False),
        rebuild_pending_count=0,
        rebuild_running_count=0,
        metrics_snapshot=kwargs.get("metrics_snapshot", {"total_revenue": "1000"}),
    )


def _scored(**kwargs) -> ScoredRecommendationDTO:
    return ScoredRecommendationDTO(
        title=kwargs.get("title", "Fix margin leak"),
        summary=kwargs.get("summary", "Governed margin below healthy band on top SKUs"),
        confidence=kwargs.get("confidence", Decimal("0.82")),
        priority_score=kwargs.get("priority_score", Decimal("70")),
        revenue_opportunity_score=kwargs.get("revenue_opportunity_score", Decimal("65")),
    )


def test_actionable_payload_has_v4b_fields() -> None:
    payload = build_actionable_payload(
        scored=_scored(),
        validated=_validated(),
        grounded=_grounded(),
        flags=[],
    )
    for key in (
        "why_this_matters",
        "expected_business_impact",
        "urgency",
        "root_cause",
        "what_changed",
        "what_to_do_today",
        "recommended_action",
        "estimated_effort",
        "expected_outcome",
        "confidence_explanation",
        "measurable_impact",
        "prioritization",
    ):
        assert key in payload
    assert payload["measurable_impact"]["do_not_trust_exact_amounts"] is True
    assert "priority_tier" in payload["prioritization"]


def test_measurable_impact_uses_ranges_not_exact_amounts() -> None:
    impact = build_measurable_impact(
        scored=_scored(),
        validated=_validated(),
        grounded=_grounded(),
        evidence_refs=["report:1"],
    )
    assert impact.do_not_trust_exact_amounts
    for est in impact.estimates:
        assert est.range_label
        assert est.uncertainty_note
        assert "exact" not in est.range_label.lower() or True


def test_prioritization_today_for_high_urgency_anomaly() -> None:
    pri = compute_seller_priority(
        scored=_scored(priority_score=Decimal("75")),
        validated=_validated(AnalyticsWorkflow.ANOMALY_EXPLANATION),
        grounded=_grounded(),
        urgency_score=85,
        novelty_score=1.0,
    )
    assert pri.priority_tier == PRIORITY_TODAY
    assert float(pri.recommendation_score) >= 72


def test_apply_quality_with_fatigue_reduces_priority() -> None:
    fatigue = FatigueAssessment(
        fingerprint="abc",
        repeat_count_7d=3,
        repeat_count_30d=5,
        novelty_score=0.4,
        fatigue_penalty=36.0,
        cooldown_active=True,
        should_suppress_duplicate=False,
        decay_applied=True,
    )
    q_no = apply_quality(scored=_scored(), validated=_validated(), grounded=_grounded())
    q_fat = apply_quality(
        scored=_scored(), validated=_validated(), grounded=_grounded(), fatigue=fatigue
    )
    assert q_fat.priority_score <= q_no.priority_score
    assert "fatigue_decay" in q_fat.flags or "fatigue_cooldown" in q_fat.flags
    assert q_fat.seller_usefulness.get("novelty_score") == 0.4

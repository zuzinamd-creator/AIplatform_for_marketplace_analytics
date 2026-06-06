"""Unit tests for REAL-AI-3 seller productization."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.product.conversation import answer_follow_up
from app.ai.product.seller_usefulness import build_seller_usefulness
from app.ai.quality.recommendation_quality import apply_quality
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO
from app.models.ai_intelligence import AIRecommendation, RiskClass, SellerWorkflowState


def _validated() -> ValidatedInsightDTO:
    return ValidatedInsightDTO(
        title="Margin advisory",
        summary="Low margin on governed KPIs",
        confidence=Decimal("0.75"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        semantics_version="1.0",
    )


def _grounded() -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
    )


def test_seller_usefulness_has_required_fields() -> None:
    scored = ScoredRecommendationDTO(
        title="t",
        summary="s",
        confidence=Decimal("0.8"),
        priority_score=Decimal("60"),
    )
    u = build_seller_usefulness(scored=scored, validated=_validated(), grounded=_grounded(), flags=[])
    assert u.why_this_matters
    assert u.expected_business_impact
    assert u.urgency in ("today", "this_week", "when_convenient", "сегодня", "на этой неделе", "когда будет время")
    assert u.concrete_next_action
    assert u.confidence_explanation
    assert u.limitations


def test_apply_quality_includes_seller_usefulness() -> None:
    scored = ScoredRecommendationDTO(
        title="t",
        summary="s",
        confidence=Decimal("0.8"),
        priority_score=Decimal("60"),
    )
    q = apply_quality(scored=scored, validated=_validated(), grounded=_grounded())
    assert "why_this_matters" in q.seller_usefulness
    assert "prioritization" in q.seller_usefulness
    assert "measurable_impact" in q.seller_usefulness
    assert "root_cause" in q.seller_usefulness


def test_conversation_why_from_stored_plan() -> None:
    rec = AIRecommendation(
        user_id=uuid4(),
        workflow_type="revenue_insight",
        risk_class=RiskClass.LOW,
        title="t",
        summary="s",
        action_plan={
            "seller_usefulness": {
                "why_this_matters": "Margin below healthy band on governed report.",
            }
        },
    )
    reply = answer_follow_up(rec, question="why")
    assert "Margin below" in reply.answer
    assert reply.advisory_only is True


def test_seller_workflow_state_enum() -> None:
    assert SellerWorkflowState.SNOOZED.value == "snoozed"

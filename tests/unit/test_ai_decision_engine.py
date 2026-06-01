"""Unit tests for AI decision engine scoring."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.ai.decision.engine import AIDecisionEngine
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO


def _validated(
    *,
    workflow: AnalyticsWorkflow = AnalyticsWorkflow.REVENUE_INSIGHT,
    unsupported_claims: list[str] | None = None,
) -> ValidatedInsightDTO:
    return ValidatedInsightDTO(
        title="Revenue advisory",
        summary="Advisory summary for operator review",
        confidence=Decimal("0.85"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=workflow,
        semantics_version="1.0",
        unsupported_claims=unsupported_claims or [],
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
        metrics_snapshot={"total_revenue": 50000},
    )


def test_priority_boost_for_risk_workflow() -> None:
    engine = AIDecisionEngine()
    risk = engine.score_recommendation(
        validated=_validated(workflow=AnalyticsWorkflow.RISK_DETECTION),
        grounded=_grounded(),
    )
    revenue = engine.score_recommendation(
        validated=_validated(workflow=AnalyticsWorkflow.REVENUE_INSIGHT),
        grounded=_grounded(),
    )
    assert risk.priority_score > revenue.priority_score


def test_recommendation_workflow_requires_approval() -> None:
    scored = AIDecisionEngine().score_recommendation(
        validated=_validated(workflow=AnalyticsWorkflow.RECOMMENDATION),
        grounded=_grounded(),
    )
    assert scored.requires_human_approval is True
    assert scored.approval_category == "pricing_change"


def test_unsupported_claims_raise_risk() -> None:
    scored = AIDecisionEngine().score_recommendation(
        validated=_validated(unsupported_claims=["unverified margin claim"]),
        grounded=_grounded(),
    )
    assert scored.risk_class.value == "high"

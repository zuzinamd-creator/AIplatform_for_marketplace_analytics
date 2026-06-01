"""Deterministic prompt v3 evaluation fixtures."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from app.ai.prompts.v3.render import render_prompt_v3
from app.ai.quality.recommendation_quality import apply_quality
from app.ai.validation.insight_validator import validate_insight_output
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


def _grounded(*, degraded: bool = False, metrics: dict | None = None) -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=degraded,
        rebuild_pending_count=5 if degraded else 0,
        rebuild_running_count=0,
        metrics_snapshot={"total_revenue": "1000"} if metrics is None else metrics,
    )


def eval_v3_prompt_has_governance_rules() -> bool:
    rendered = render_prompt_v3(grounded=_grounded(), workflow="revenue_insight")
    return (
        "NEVER invent KPIs" in rendered.system
        and "confidence_hint" in rendered.system
        and rendered.output_schema == "AnalyticalInsightJSONv3"
    )


def eval_stale_data_caps_confidence() -> bool:
    grounded = _grounded(degraded=True)
    raw = json.dumps(
        {
            "summary": "Stale advisory",
            "bullets": ["check data"],
            "confidence_hint": 0.95,
        }
    )
    validated = validate_insight_output(
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        grounded=grounded,
        raw_output=raw,
    )
    return validated.stale_data_warning and validated.confidence <= Decimal("0.7")


def eval_unsupported_claims_flagged() -> bool:
    grounded = _grounded(metrics={})
    raw = "Revenue jumped to 9999999 rub this week per our analysis"
    validated = validate_insight_output(
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        grounded=grounded,
        raw_output=raw,
    )
    return len(validated.unsupported_claims) > 0


def eval_usefulness_payload_present() -> bool:
    scored = ScoredRecommendationDTO(
        title="t",
        summary="s",
        confidence=Decimal("0.7"),
        priority_score=Decimal("50"),
    )
    validated = ValidatedInsightDTO(
        title="t",
        summary="s",
        confidence=Decimal("0.7"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        semantics_version="1.0",
    )
    q = apply_quality(scored=scored, validated=validated, grounded=_grounded())
    su = q.seller_usefulness
    action = su.get("recommended_action") or su.get("concrete_next_action")
    return bool(
        su.get("why_this_matters")
        and action
        and su.get("prioritization")
        and su.get("measurable_impact")
    )


def eval_prioritization_in_prompt() -> bool:
    rendered = render_prompt_v3(grounded=_grounded(), workflow="anomaly_explanation")
    return "Prioritization" in rendered.system and "severity" in rendered.system.lower()


def run_prompt_v3_eval_suite() -> list[tuple[str, bool]]:
    cases = [
        ("governance_rules", eval_v3_prompt_has_governance_rules),
        ("stale_data", eval_stale_data_caps_confidence),
        ("unsupported_claims", eval_unsupported_claims_flagged),
        ("usefulness_payload", eval_usefulness_payload_present),
        ("prioritization_rules", eval_prioritization_in_prompt),
    ]
    return [(name, fn()) for name, fn in cases]

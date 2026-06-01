#!/usr/bin/env python3
"""REAL-AI-3 seller scenario validation (deterministic modules, no live marketplace)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.product.conversation import answer_follow_up
from app.ai.quality.recommendation_quality import apply_quality
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import RiskClassification, ScoredRecommendationDTO
from app.dto.analytics_dto import AIInsightInputDTO, AnomalyDTO, ContextDTO, MetricsDTO
from app.models.ai_intelligence import AIRecommendation, RecommendationStatus, RiskClass

SCENARIOS = (
    "strong_store",
    "weak_store",
    "stockout_signal",
    "ads_overspend_limited_data",
    "declining_conversion_anomaly",
    "real_export_shape",
)


def _grounded(*, degraded: bool = False) -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=degraded,
        rebuild_pending_count=3 if degraded else 0,
        rebuild_running_count=0,
    )


def _insight_for(scenario: str) -> AIInsightInputDTO:
    base = dict(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date.today(),
            marketplace_type="wildberries",
        ),
    )
    if scenario == "strong_store":
        return AIInsightInputDTO(
            **base,
            metrics=MetricsDTO(
                sku_count=50,
                total_revenue=Decimal("500000"),
                total_profit=Decimal("120000"),
                margin=Decimal("0.24"),
            ),
        )
    if scenario == "weak_store":
        return AIInsightInputDTO(
            **base,
            metrics=MetricsDTO(sku_count=8, total_revenue=Decimal("8000"), total_profit=Decimal("400"), margin=Decimal("0.05")),
        )
    if scenario == "stockout_signal":
        return AIInsightInputDTO(**base, metrics=MetricsDTO(sku_count=12, total_revenue=Decimal("40000"), total_profit=Decimal("5000")))
    if scenario == "ads_overspend_limited_data":
        return AIInsightInputDTO(**base, metrics=MetricsDTO(sku_count=20, total_revenue=Decimal("100000"), total_profit=Decimal("10000"), margin=Decimal("0.1")))
    if scenario == "declining_conversion_anomaly":
        return AIInsightInputDTO(
            **base,
            metrics=MetricsDTO(sku_count=15, total_revenue=Decimal("30000"), total_profit=Decimal("2000"), margin=Decimal("0.07")),
            anomalies=[
                AnomalyDTO(
                    type="data_quality",
                    severity="high",
                    confidence=Decimal("0.88"),
                    message="Conversion column missing in export — KPIs may be incomplete",
                )
            ],
        )
    return AIInsightInputDTO(
        **base,
        metrics=MetricsDTO(sku_count=25, total_revenue=Decimal("75000"), total_profit=Decimal("9000"), margin=Decimal("0.12")),
    )


def _run_scenario(name: str) -> list[str]:
    errors: list[str] = []
    _insight_for(name)
    validated = ValidatedInsightDTO(
        title=f"Scenario {name}",
        summary="Advisory summary for seller validation",
        confidence=Decimal("0.8"),
        degraded_mode=name == "declining_conversion_anomaly",
        stale_data_warning=name == "declining_conversion_anomaly",
        evidence_complete=True,
        workflow=AnalyticsWorkflow.ANOMALY_EXPLANATION if "anomaly" in name else AnalyticsWorkflow.REVENUE_INSIGHT,
        semantics_version="1.0",
    )
    scored = ScoredRecommendationDTO(
        title=validated.title,
        summary=validated.summary,
        confidence=validated.confidence,
        priority_score=Decimal("65"),
        risk_class=RiskClassification.MEDIUM,
    )
    grounded = _grounded(degraded="anomaly" in name or name == "weak_store")
    quality = apply_quality(scored=scored, validated=validated, grounded=grounded)
    su = quality.seller_usefulness
    required = (
        "why_this_matters",
        "expected_business_impact",
        "urgency",
        "recommended_action",
        "root_cause",
        "prioritization",
        "confidence_explanation",
    )
    for k in required:
        if not su.get(k):
            errors.append(f"{name}: missing seller_usefulness.{k}")

    fake_rec = AIRecommendation(
        user_id=uuid4(),
        workflow_type=validated.workflow.value,
        status=RecommendationStatus.DRAFT,
        risk_class=RiskClass.LOW,
        title="t",
        summary=validated.summary,
        action_plan={"seller_usefulness": su},
        reasoning_trace={},
    )
    reply = answer_follow_up(fake_rec, question="why")
    if len(reply.answer) < 10:
        errors.append(f"{name}: empty why answer")
    return errors


def main() -> int:
    all_errors: list[str] = []
    for s in SCENARIOS:
        all_errors.extend(_run_scenario(s))
    if all_errors:
        for e in all_errors:
            print(f"FAIL: {e}")
        return 1
    print(f"OK: {len(SCENARIOS)} seller scenarios passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

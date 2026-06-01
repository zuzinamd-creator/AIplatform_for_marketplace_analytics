"""Insight validation heuristics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.validation import validate_insight_output
from app.dto.ai_analytics_dto import AnalyticsWorkflow, EvidenceRefDTO, GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO, ContextDTO, MetricsDTO


def test_stale_context_lowers_confidence() -> None:
    grounded = GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=None,
        source_period_end=None,
        degraded_mode=True,
        rebuild_pending_count=2,
        rebuild_running_count=1,
        evidence=(),
        metrics_snapshot={},
        freshness_note="rebuild in progress",
    )
    validated = validate_insight_output(
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        grounded=grounded,
        raw_output='{"summary":"test","bullets":[],"confidence_hint":0.9}',
    )
    assert validated.stale_data_warning is True
    assert validated.confidence <= Decimal("0.6")


def test_evidence_complete_with_insight() -> None:
    dto = AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=datetime.now(UTC).date(),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(sku_count=1, total_revenue=Decimal("100")),
    )
    grounded = GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=dto.context.report_date,
        source_period_end=dto.context.report_date,
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
        evidence=(
            EvidenceRefDTO(
                source_type="report",
                source_id=str(dto.context.report_id),
                label="report",
            ),
        ),
        metrics_snapshot=dto.to_legacy_dict(),
        freshness_note="current",
    )
    validated = validate_insight_output(
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        grounded=grounded,
        raw_output='{"summary":"ok","bullets":["a"],"confidence_hint":0.8}',
    )
    assert validated.evidence_complete is True

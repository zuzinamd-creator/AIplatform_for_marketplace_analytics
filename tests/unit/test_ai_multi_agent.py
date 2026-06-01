"""Unit tests for multi-agent coordination pipeline."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.coordination.coordinator import MultiAgentCoordinator
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO


def test_coordinator_produces_recommendation_and_plan() -> None:
    validated = ValidatedInsightDTO(
        title="Anomaly",
        summary="Pattern detected in SKU metrics",
        confidence=Decimal("0.72"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=AnalyticsWorkflow.ANOMALY_EXPLANATION,
        semantics_version="1.0",
    )
    grounded = GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
    )
    result = MultiAgentCoordinator().coordinate(
        run_id=uuid4(),
        validated=validated,
        grounded=grounded,
    )
    assert result.recommendation.confidence == Decimal("0.72")
    assert len(result.action_plan.steps) >= 3
    assert len(result.agent_messages) >= 3
    assert result.explainability.summary_for_operator

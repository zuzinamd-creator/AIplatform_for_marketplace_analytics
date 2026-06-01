"""Typed AI analytics contracts (grounding, validation, workflows)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsWorkflow(StrEnum):
    ANOMALY_EXPLANATION = "anomaly_explanation"
    TREND_EXPLANATION = "trend_explanation"
    REVENUE_INSIGHT = "revenue_insight"
    INVENTORY_INSIGHT = "inventory_insight"
    CAUSAL_ANALYSIS = "causal_analysis"
    RECOMMENDATION = "recommendation"
    RISK_DETECTION = "risk_detection"
    FORECAST_PREP = "forecast_prep"


class EvidenceRefDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    source_type: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=256)
    period_start: date | None = None
    period_end: date | None = None


class GroundedContextDTO(BaseModel):
    """Factual grounding package passed to LLM adapters."""

    model_config = ConfigDict(strict=True, frozen=True)

    semantics_version: str
    data_as_of: datetime
    source_period_start: date | None
    source_period_end: date | None
    degraded_mode: bool
    rebuild_pending_count: int
    rebuild_running_count: int
    evidence: tuple[EvidenceRefDTO, ...] = ()
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    freshness_note: str = ""


class ValidatedInsightDTO(BaseModel):
    """Advisory insight after validation heuristics."""

    model_config = ConfigDict(strict=True)

    title: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    confidence: Decimal = Field(ge=0, le=1)
    degraded_mode: bool
    stale_data_warning: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    evidence_complete: bool
    workflow: AnalyticsWorkflow
    semantics_version: str
    raw_model_output: str = ""


class AIRunRequestDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    workflow: AnalyticsWorkflow
    prompt_id: str
    semantics_version: str = "1.0"
    session_id: UUID | None = None
    report_id: UUID | None = None

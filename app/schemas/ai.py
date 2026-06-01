"""AI API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.dto.ai_analytics_dto import AnalyticsWorkflow
from app.models.ai_execution import AIExecutionStatus


class PageMeta(BaseModel):
    total: int
    skip: int
    limit: int


class AIRunCreateRequest(BaseModel):
    workflow: AnalyticsWorkflow
    prompt_id: str
    semantics_version: str = "1.0"
    session_id: UUID | None = None
    report_id: UUID | None = None


class AIRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_kind: str
    status: AIExecutionStatus
    prompt_id: str
    prompt_version: str
    semantics_version: str
    context_valid: bool
    degraded_mode: bool
    tokens_used: int
    tool_call_count: int
    duration_ms: int | None
    output_insight_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None


class AIRunDetailResponse(AIRunResponse):
    last_error: str | None = None
    correlation_id: str | None = None


class PaginatedAIRunsResponse(BaseModel):
    items: list[AIRunResponse]
    page: PageMeta


class AIInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    insight_type: str
    status: str
    title: str | None
    summary: str | None
    workflow_type: str | None
    confidence_score: Decimal | None
    context_payload: dict | None
    advisory_metadata: dict | None
    created_at: datetime


class PaginatedAIInsightsResponse(BaseModel):
    items: list[AIInsightResponse]
    page: PageMeta


class AIExecutionResultResponse(BaseModel):
    run: AIRunDetailResponse
    insight_id: UUID | None
    confidence: Decimal
    degraded_mode: bool
    stale_data_warning: bool
    summary: str

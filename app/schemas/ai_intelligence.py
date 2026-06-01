"""AI intelligence API schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.dto.ai_analytics_dto import AnalyticsWorkflow
from app.schemas.ai import PageMeta


class IntelligenceRunCreateRequest(BaseModel):
    workflow: AnalyticsWorkflow
    prompt_id: str
    semantics_version: str = "1.0"
    session_id: UUID | None = None
    report_id: UUID | None = None


class PeriodIntelligenceRunCreateRequest(BaseModel):
    """Run intelligence for a selected analytical period (no raw report access)."""

    workflow: AnalyticsWorkflow
    prompt_id: str
    semantics_version: str = "1.0"
    session_id: UUID | None = None
    marketplace: str = Field(min_length=1, max_length=32, default="wildberries")
    period_start: date
    period_end: date


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_type: str
    status: str
    risk_class: str
    title: str
    summary: str
    confidence_score: Decimal | None
    priority_score: Decimal | None
    requires_human_approval: bool
    action_plan: dict | None = None
    lineage: dict | None = None
    run_id: UUID | None
    insight_id: UUID | None
    created_at: datetime
    seller_workflow_state: str = "active"
    snoozed_until: datetime | None = None


class RecommendationWorkflowRequest(BaseModel):
    action: str = Field(description="complete | snooze | dismiss | save | reactivate")
    snooze_days: int | None = Field(default=7, ge=1, le=90)


class RecommendationAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ConversationReplyResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    advisory_only: bool = True


class DigestSectionResponse(BaseModel):
    title: str
    body: str
    priority: str


class AIDigestResponse(BaseModel):
    digest_type: str
    generated_at: datetime
    headline: str
    sections: list[DigestSectionResponse]
    active_recommendation_count: int
    advisory_notice: str


class UsefulnessMetricsResponse(BaseModel):
    total_recommendations: int
    accepted_count: int
    rejected_count: int
    ignored_count: int
    completed_count: int
    dismissed_count: int
    saved_count: int
    snoozed_count: int
    repeated_fingerprint_count: int
    fatigue_top_fingerprints: list[dict] = Field(default_factory=list)
    action_conversion_rate: float | None = None
    helpful_rate: float | None = None
    usefulness_score: float | None = None
    repeated_dismissals: int = 0
    feedback_trend: str = "stable"


class PriorityQueueItemResponse(BaseModel):
    recommendation_id: str
    title: str
    summary: str
    recommendation_score: float
    priority_tier: str
    priority_score: float | None = None
    seller_usefulness: dict = Field(default_factory=dict)


class TodaysFocusResponse(BaseModel):
    generated_at: datetime
    headline: str
    requires_attention_today: list[str]
    can_wait: list[str]
    dangerous: list[str]
    highest_upside: list[str]
    top_actions: list[dict]
    critical_alerts: list[dict]
    quick_wins: list[dict]
    priority_queue: list[PriorityQueueItemResponse]
    advisory_notice: str


class RecommendationStatsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    total: int
    ignored_7d: int
    avg_rating: float | None
    helpful_rate: float | None
    accept_rate: float | None
    reject_rate: float | None
    fatigue_top_fingerprints: list[dict] = Field(default_factory=list)
    action_conversion_rate: float | None = None
    completed_count: int = 0
    dismissed_count: int = 0


class ExplainabilityResponse(BaseModel):
    summary_for_operator: str
    confidence_rationale: str
    evidence_graph: dict
    reasoning_trace: dict
    provenance: dict
    freshness_score: Decimal
    trust_context: dict = Field(default_factory=dict)


class IntelligenceRunResponse(BaseModel):
    run_id: UUID
    insight_id: UUID | None
    recommendation_id: UUID | None
    recommendation: RecommendationResponse | None = None
    explainability: ExplainabilityResponse | None = None
    confidence: Decimal
    requires_human_approval: bool
    summary: str


class PaginatedRecommendationsResponse(BaseModel):
    items: list[RecommendationResponse]
    page: PageMeta


class RecommendationFeedbackRequest(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    helpful: bool | None = None
    override_reason: str | None = None
    feedback_type: str = "general"


class AIOperationalStatusResponse(BaseModel):
    overall_score: float
    degraded_intelligence_mode: bool
    runs_total: int
    success_rate: float
    pending_approvals: int
    avg_confidence: float | None
    recommendations: list[str]

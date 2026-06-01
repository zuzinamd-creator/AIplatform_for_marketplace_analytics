"""AI intelligence DTOs — recommendations, explainability, planning."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO


class AgentRole(StrEnum):
    PLANNER = "planner"
    ANALYST = "analyst"
    VALIDATOR = "validator"
    OPERATIONS_ADVISOR = "operations_advisor"
    COORDINATOR = "coordinator"


class RiskClassification(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PlanStepDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    step_id: str
    agent_role: AgentRole
    description: str
    depends_on: tuple[str, ...] = ()
    simulated: bool = True


class ActionPlanDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    plan_id: str
    workflow: AnalyticsWorkflow
    steps: tuple[PlanStepDTO, ...]
    dependency_notes: str = ""


class ScoredRecommendationDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    confidence: Decimal = Field(ge=0, le=1)
    priority_score: Decimal = Field(ge=0, le=100)
    revenue_opportunity_score: Decimal = Field(ge=0, le=100, default=Decimal("0"))
    risk_class: RiskClassification = RiskClassification.LOW
    requires_human_approval: bool = False
    approval_category: str | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class EvidenceNodeDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    node_id: str
    label: str
    source_type: str
    source_id: str
    supports_claim: str | None = None


class EvidenceGraphDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    nodes: tuple[EvidenceNodeDTO, ...]
    edges: tuple[tuple[str, str, str], ...] = ()


class ReasoningStepDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    agent_role: AgentRole
    step: str
    detail: str
    confidence_contribution: Decimal = Decimal("0")


class ExplainabilityDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    summary_for_operator: str
    confidence_rationale: str
    evidence_graph: EvidenceGraphDTO
    reasoning_trace: tuple[ReasoningStepDTO, ...]
    provenance: dict[str, str] = Field(default_factory=dict)
    freshness_score: Decimal = Decimal("1.0")


class AgentMessageDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    from_role: AgentRole
    to_role: AgentRole
    message_type: str
    payload_summary: str


class IntelligenceRunResultDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    run_id: UUID
    recommendation: ScoredRecommendationDTO
    action_plan: ActionPlanDTO
    explainability: ExplainabilityDTO
    agent_messages: tuple[AgentMessageDTO, ...]
    grounded: GroundedContextDTO
    insight_id: UUID | None = None
    recommendation_id: UUID | None = None

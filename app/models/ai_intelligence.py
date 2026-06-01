"""AI intelligence persistence — recommendations, memory, feedback (advisory-only)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class RecommendationStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class RiskClass(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SellerWorkflowState(str, enum.Enum):
    ACTIVE = "active"
    SAVED = "saved"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"
    COMPLETED = "completed"


class AIRecommendation(Base, TenantMixin, TimestampMixin):
    __tablename__ = "ai_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    parent_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, name="recommendation_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=RecommendationStatus.DRAFT,
        nullable=False,
    )
    risk_class: Mapped[RiskClass] = mapped_column(
        Enum(RiskClass, name="recommendation_risk_class_enum", values_callable=lambda x: [e.value for e in x]),
        default=RiskClass.LOW,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    requires_human_approval: Mapped[bool] = mapped_column(default=False, nullable=False)
    action_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evidence_graph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reasoning_trace: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    lineage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seller_workflow_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SellerWorkflowState.ACTIVE.value, index=True
    )
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIStrategicMemory(Base, TenantMixin, TimestampMixin):
    __tablename__ = "ai_strategic_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AIRecommendationFeedback(Base, TenantMixin, TimestampMixin):
    __tablename__ = "ai_recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recommendation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    rating: Mapped[int | None] = mapped_column(nullable=True)
    helpful: Mapped[bool | None] = mapped_column(nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False, default="general")

"""AI execution run audit metadata (tenant-scoped)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AIExecutionStatus(str, enum.Enum):
    REQUESTED = "requested"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEGRADED = "degraded"


class AIExecutionRun(Base, TenantMixin, TimestampMixin):
    """Audit trail for governed AI runs (lifecycle, budgets, tool-call events)."""

    __tablename__ = "ai_execution_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[AIExecutionStatus] = mapped_column(
        Enum(
            AIExecutionStatus,
            name="ai_execution_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AIExecutionStatus.REQUESTED,
    )
    prompt_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False)
    context_valid: Mapped[bool] = mapped_column(nullable=False, default=False)
    degraded_mode: Mapped[bool] = mapped_column(nullable=False, default=False)
    token_budget: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_events: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    runtime_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_insight_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

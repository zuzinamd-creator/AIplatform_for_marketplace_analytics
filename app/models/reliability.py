"""Reliability persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProcessKind(StrEnum):
    ETL_WORKER = "etl_worker"
    ORCHESTRATOR = "orchestrator"
    API = "api"


class TenantContainmentStatus(StrEnum):
    HEALTHY = "healthy"
    THROTTLED = "throttled"
    QUARANTINED = "quarantined"


class RuntimeProcessHeartbeat(Base, TimestampMixin):
    __tablename__ = "runtime_process_heartbeats"

    process_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    process_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class RuntimeProcessLease(Base, TimestampMixin):
    __tablename__ = "runtime_process_leases"

    lease_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    holder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class TenantContainmentState(Base, TimestampMixin):
    __tablename__ = "tenant_containment_states"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TenantContainmentStatus.HEALTHY)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    throttled_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OperatorAuditEvent(Base, TimestampMixin):
    __tablename__ = "operator_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

"""Enterprise autonomous operations persistence."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class AutonomousActionStatus(str, enum.Enum):
    PLANNED = "planned"
    EXECUTED = "executed"
    SIMULATED = "simulated"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"


class RuntimeAutonomousAction(Base, TimestampMixin):
    """Autonomous action journal with provenance and lineage."""

    __tablename__ = "runtime_autonomous_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    decision_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[AutonomousActionStatus] = mapped_column(
        Enum(
            AutonomousActionStatus,
            name="autonomous_action_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AutonomousActionStatus.PLANNED,
        nullable=False,
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reversible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    lineage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class RuntimeSchedulePolicy(Base, TenantMixin, TimestampMixin):
    """Tenant scheduling policy — maintenance windows and blackout periods."""

    __tablename__ = "runtime_schedule_policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    maintenance_windows: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    blackout_periods: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fairness_weight: Mapped[float | None] = mapped_column(nullable=True)
    rebuild_priority_bias: Mapped[float | None] = mapped_column(nullable=True)
    adaptive_rebuild_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

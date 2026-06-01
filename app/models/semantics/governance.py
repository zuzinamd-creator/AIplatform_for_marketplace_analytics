import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class SemanticsLifecycleStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class SemanticsLifecycleVersion(Base):
    """Central semantics lifecycle registry (global, not tenant-scoped)."""

    __tablename__ = "semantics_lifecycle_versions"

    version: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[SemanticsLifecycleStatus] = mapped_column(
        SAEnum(
            SemanticsLifecycleStatus,
            name="semantics_lifecycle_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    introduced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supported_for_rebuild: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supported_for_ingest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RebuildOrchestrationStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEFERRED = "deferred"


class RebuildMode(str, enum.Enum):
    INCREMENTAL = "incremental"
    FULL = "full"


class SnapshotRebuildRequirement(Base, TenantMixin):
    __tablename__ = "snapshot_rebuild_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    semantics_version: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("semantics_lifecycle_versions.version", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    requires_rebuild: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    orchestration_status: Mapped[RebuildOrchestrationStatus] = mapped_column(
        SAEnum(
            RebuildOrchestrationStatus,
            name="rebuild_orchestration_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=RebuildOrchestrationStatus.PENDING,
    )
    rebuild_mode: Mapped[RebuildMode] = mapped_column(
        SAEnum(
            RebuildMode,
            name="rebuild_mode_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=RebuildMode.INCREMENTAL,
    )
    priority: Mapped[int] = mapped_column(nullable=False, default=100)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_eligible_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class SemanticsChangeLog(Base):
    __tablename__ = "semantics_change_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    old_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_version: Mapped[str] = mapped_column(String(16), nullable=False)
    changed_operations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    migration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

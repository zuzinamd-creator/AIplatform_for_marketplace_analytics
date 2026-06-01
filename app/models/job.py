import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class EtlJob(Base, TenantMixin, TimestampMixin):
    """Dedicated queue entity. Reports hold business data only."""

    __tablename__ = "etl_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_etl_job_tenant_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="etl_process_report")
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    visibility_timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Denormalized snapshot — queue broker must not read reports table
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    marketplace: Mapped[str] = mapped_column(String(32), nullable=False, default="wildberries")
    report_type: Mapped[str] = mapped_column(String(32), nullable=False, default="sales")
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False, default="report.csv")
    report_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

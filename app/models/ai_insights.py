import enum
import uuid

from sqlalchemy import Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class InsightStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    ARCHIVED = "archived"


class AIInsight(Base, TenantMixin, TimestampMixin):
    """Prepared data slots for future AI layer — no AI logic in MVP."""

    __tablename__ = "ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    insight_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[InsightStatus] = mapped_column(
        Enum(InsightStatus, name="insight_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=InsightStatus.PENDING,
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_metric_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    workflow_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    advisory_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

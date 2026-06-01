import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class NormalizedReportRow(Base, TenantMixin, TimestampMixin):
    __tablename__ = "normalized_report_rows"
    __table_args__ = (
        UniqueConstraint("report_id", "source_row_id", name="uq_normalized_report_source_row"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    operation_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nm_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    canonical_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

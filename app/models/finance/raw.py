import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class RawReport(Base, TenantMixin, TimestampMixin):
    """Immutable ingest record; file bytes live in object storage."""

    __tablename__ = "raw_reports"
    __table_args__ = (UniqueConstraint("report_id", name="uq_raw_report_report_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ingest_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

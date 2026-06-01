import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Marketplace(str, enum.Enum):
    WILDBERRIES = "wildberries"
    OZON = "ozon"
    COSTS = "costs"


class ReportType(str, enum.Enum):
    SALES = "sales"
    ORDERS = "orders"
    STOCK = "stock"
    FINANCE = "finance"
    COSTS = "costs"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Report(Base, TenantMixin, TimestampMixin):
    """Business entity only. Queue state lives in etl_jobs."""

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("user_id", "file_checksum", name="uq_report_tenant_checksum"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, name="report_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Legacy column; API status is projected from etl_jobs (see report_projection.py).
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=ReportStatus.PENDING,
        nullable=False,
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

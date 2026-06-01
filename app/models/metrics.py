import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.report import Marketplace


class MetricPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class Metric(Base, TenantMixin, TimestampMixin):
    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "internal_sku",
            "marketplace",
            "period",
            "period_start",
            name="uq_metric_tenant_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    internal_sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    period: Mapped[MetricPeriod] = mapped_column(
        Enum(MetricPeriod, name="metric_period_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    orders_count: Mapped[int | None] = mapped_column(nullable=True)
    units_sold: Mapped[int | None] = mapped_column(nullable=True)
    margin: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    kpi_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

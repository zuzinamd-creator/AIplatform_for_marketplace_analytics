import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.report import Marketplace


class DailyAggregate(Base, TenantMixin, TimestampMixin):
    __tablename__ = "daily_aggregates"
    __table_args__ = (
        UniqueConstraint("aggregate_date", "marketplace", name="uq_daily_aggregate_day_marketplace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    net_profit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    roi: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    return_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    buyout_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    average_check: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class SkuDailyMetric(Base, TenantMixin, TimestampMixin):
    __tablename__ = "sku_daily_metrics"
    __table_args__ = (
        UniqueConstraint("sku", "metric_date", "marketplace", name="uq_sku_daily_metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    net_profit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    margin: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    roi: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    return_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    buyout_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    average_check: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

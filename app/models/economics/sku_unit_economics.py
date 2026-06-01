import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.report import Marketplace


class SkuUnitEconomicsDaily(Base, TenantMixin, TimestampMixin):
    """
    Daily SKU-level unit economics projection (rebuildable from append-only ledgers + costs).

    Additive projection only: never becomes authoritative; can be recomputed.
    """

    __tablename__ = "sku_unit_economics_daily"
    __table_args__ = (
        UniqueConstraint(
            "sku",
            "metric_date",
            "marketplace",
            name="uq_sku_unit_econ_daily",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    returns_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    payout: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    commissions: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    logistics: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    storage: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    ads: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    penalties: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    acquiring: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    deductions: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    compensation: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    # Not yet represented explicitly in LedgerOperationType in this repo snapshot.
    acceptance_fees: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    loyalty_compensation: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    cogs: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    contribution_margin: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))

    margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    return_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    ad_cost_ratio: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    logistics_burden: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)


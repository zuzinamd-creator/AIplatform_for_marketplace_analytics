import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class WarehouseStockSnapshot(Base, TenantMixin):
    """Daily deterministic warehouse stock state (rebuildable from inventory ledger)."""

    __tablename__ = "warehouse_stock_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "snapshot_date",
            "sku",
            "warehouse_name",
            name="uq_warehouse_stock_snapshot_day_sku_wh",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nm_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warehouse_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    opening_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    inbound_units: Mapped[int] = mapped_column(Integer, nullable=False)
    sold_units: Mapped[int] = mapped_column(Integer, nullable=False)
    returned_units: Mapped[int] = mapped_column(Integer, nullable=False)
    lost_units: Mapped[int] = mapped_column(Integer, nullable=False)
    writeoff_units: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_closing_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    discrepancy_units: Mapped[int] = mapped_column(Integer, nullable=False)
    discrepancy_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    discrepancy_sale_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

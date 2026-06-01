import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class WarehouseStockSnapshotStaging(Base, TenantMixin):
    """Atomic full-rebuild staging; swapped into warehouse_stock_snapshots in one transaction."""

    __tablename__ = "warehouse_stock_snapshots_staging"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rebuild_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
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
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

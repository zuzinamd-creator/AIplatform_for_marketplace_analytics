import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin
from app.models.inventory.enums import InventoryOperationType


class InventoryLedgerEntry(Base, TenantMixin):
    """Append-only inventory movement ledger (separate from financial_ledger_entries)."""

    __tablename__ = "inventory_ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "source_row_id",
            "operation_type",
            name="uq_inventory_ledger_report_source_operation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    nm_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warehouse_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    operation_type: Mapped[InventoryOperationType] = mapped_column(
        Enum(
            InventoryOperationType,
            name="inventory_operation_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    sale_price_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_cost_delta: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_sale_delta: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source_row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    canonical_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

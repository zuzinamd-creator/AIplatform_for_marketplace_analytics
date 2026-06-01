import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.finance.enums import LedgerOperationType


class FinancialLedgerEntry(Base, TenantMixin, TimestampMixin):
    __tablename__ = "financial_ledger_entries"
    __table_args__ = (
        UniqueConstraint("report_id", "source_row_id", name="uq_ledger_report_source_row"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    normalized_row_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("normalized_report_rows.id", ondelete="SET NULL"),
        nullable=True,
    )
    operation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nm_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operation_type: Mapped[LedgerOperationType] = mapped_column(
        Enum(
            LedgerOperationType,
            name="ledger_operation_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    source_row_id: Mapped[str] = mapped_column(String(128), nullable=False)
    entry_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

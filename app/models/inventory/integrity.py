import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class InventoryIntegrityAnomalyType(str, enum.Enum):
    SNAPSHOT_DRIFT = "snapshot_drift"
    SEMANTICS_VERSION_MISSING = "semantics_version_missing"
    INCONSISTENT_OPENING_BALANCE = "inconsistent_opening_balance"
    REBUILD_GAP = "rebuild_gap"
    NEGATIVE_INVENTORY = "negative_inventory"
    CHECKSUM_MISMATCH = "checksum_mismatch"


class SnapshotConsistencyCheck(Base, TenantMixin):
    __tablename__ = "snapshot_consistency_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warehouse_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ledger_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    semantics_version: Mapped[str] = mapped_column(String(16), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_consistent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mismatch_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class InventoryIntegrityAnomaly(Base, TenantMixin):
    __tablename__ = "inventory_integrity_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    anomaly_type: Mapped[InventoryIntegrityAnomalyType] = mapped_column(
        Enum(
            InventoryIntegrityAnomalyType,
            name="inventory_integrity_anomaly_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warehouse_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

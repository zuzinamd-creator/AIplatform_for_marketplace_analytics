import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class EtlAnomalySeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EtlParserStage(str, enum.Enum):
    LOAD = "load"
    PARSE = "parse"
    NORMALIZE = "normalize"
    LEDGER = "ledger"
    INVENTORY = "inventory"
    PERSIST = "persist"
    REBUILD = "rebuild"
    VERIFICATION = "verification"


class EtlAnomalyType(str, enum.Enum):
    NEGATIVE_INVENTORY = "negative_inventory"
    IMPOSSIBLE_WAREHOUSE_TRANSITION = "impossible_warehouse_transition"
    FUTURE_DATED_OPERATION = "future_dated_operation"
    DUPLICATE_REPLAY = "duplicate_replay"
    INVALID_DECIMAL_COERCION = "invalid_decimal_coercion"
    UNSUPPORTED_SEMANTICS = "unsupported_semantics"
    SNAPSHOT_MISMATCH = "snapshot_mismatch"
    PARSE_ERROR = "parse_error"
    VALIDATION_WARNING = "validation_warning"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    SEMANTICS_INGEST_BLOCKED = "semantics_ingest_blocked"
    SEMANTICS_REBUILD_BLOCKED = "semantics_rebuild_blocked"


class EtlAnomaly(Base, TenantMixin):
    __tablename__ = "etl_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[EtlAnomalySeverity] = mapped_column(
        Enum(EtlAnomalySeverity, name="etl_anomaly_severity_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    anomaly_type: Mapped[EtlAnomalyType] = mapped_column(
        Enum(EtlAnomalyType, name="etl_anomaly_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    parser_stage: Mapped[EtlParserStage] = mapped_column(
        Enum(EtlParserStage, name="etl_parser_stage_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    normalized_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    semantics_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

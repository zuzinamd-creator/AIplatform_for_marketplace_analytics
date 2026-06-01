from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.etl.anomaly import EtlAnomalySeverity, EtlAnomalyType, EtlParserStage
from app.models.job import JobStatus
from app.models.semantics.governance import (
    RebuildMode,
    RebuildOrchestrationStatus,
    SemanticsLifecycleStatus,
)


class PageMeta(BaseModel):
    total: int
    skip: int = 0
    limit: int = Field(default=50, le=200)


class RebuildRequirementOpsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    semantics_version: str
    reason: str
    requires_rebuild: bool
    orchestration_status: RebuildOrchestrationStatus
    rebuild_mode: RebuildMode
    priority: int
    attempt_count: int
    max_attempts: int
    last_error: str | None
    last_attempted_at: datetime | None
    next_eligible_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class PaginatedRebuildsResponse(BaseModel):
    items: list[RebuildRequirementOpsResponse]
    page: PageMeta


class EtlAnomalyOpsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID | None
    source_file_name: str
    row_number: int | None
    severity: EtlAnomalySeverity
    anomaly_type: EtlAnomalyType
    parser_stage: EtlParserStage
    error_message: str
    semantics_version: str | None
    created_at: datetime


class PaginatedAnomaliesResponse(BaseModel):
    items: list[EtlAnomalyOpsResponse]
    page: PageMeta


class DriftCheckOpsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    snapshot_date: date
    sku: str | None
    warehouse_name: str | None
    ledger_hash: str
    snapshot_hash: str
    semantics_version: str
    is_consistent: bool
    mismatch_details: dict | None
    checked_at: datetime


class PaginatedDriftChecksResponse(BaseModel):
    items: list[DriftCheckOpsResponse]
    page: PageMeta


class QueueJobOpsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    report_id: UUID
    status: JobStatus
    attempt_count: int
    max_attempts: int
    visibility_timeout_seconds: int
    claimed_at: datetime | None
    processing_started_at: datetime | None
    last_heartbeat_at: datetime | None
    completed_at: datetime | None
    last_error: str | None
    created_at: datetime


class PaginatedQueueResponse(BaseModel):
    items: list[QueueJobOpsResponse]
    page: PageMeta
    status_counts: dict[str, int]


class SemanticsVersionOpsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: str
    status: SemanticsLifecycleStatus
    supported_for_rebuild: bool
    supported_for_ingest: bool
    introduced_at: datetime
    deprecated_at: datetime | None
    notes: str | None


class SemanticsStatusOpsResponse(BaseModel):
    versions: list[SemanticsVersionOpsResponse]

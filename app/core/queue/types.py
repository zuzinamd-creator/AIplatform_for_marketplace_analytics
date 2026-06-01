from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class EnqueuePayload:
    user_id: UUID
    report_id: UUID
    idempotency_key: str
    file_path: str
    marketplace: str
    report_type: str
    original_filename: str
    report_created_at: datetime
    job_type: str = "etl_process_report"
    max_attempts: int = 3
    visibility_timeout_seconds: int = 1800


@dataclass(frozen=True)
class ClaimedJobRecord:
    job_id: UUID
    report_id: UUID
    user_id: UUID
    report_created_at: datetime
    marketplace: str
    report_type: str
    original_filename: str
    file_path: str
    attempt_count: int
    max_attempts: int
    idempotency_key: str
    visibility_timeout_seconds: int


@dataclass(frozen=True)
class RecoveryRecord:
    job_id: UUID
    report_id: UUID
    user_id: UUID
    new_status: str
    last_error: str | None

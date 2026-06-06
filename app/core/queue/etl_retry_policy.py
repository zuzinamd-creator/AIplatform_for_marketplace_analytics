"""ETL job retry classification, exponential backoff, and audit metadata."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.core.config import settings


class RetryReason(StrEnum):
    LOCK_TIMEOUT = "lock_timeout"
    INVENTORY_REBUILD_BUSY = "inventory_rebuild_busy"
    WORKER_SHUTDOWN = "worker_shutdown"
    LEGACY_FILE_TOO_LARGE = "legacy_file_too_large"
    VISIBILITY_TIMEOUT = "visibility_timeout"
    SESSION_TRANSACTION = "session_transaction"
    GENERIC = "generic"


class EtlRetryableError(Exception):
    """Marks an error that should requeue the job with backoff (not immediate reclaim)."""

    def __init__(self, message: str, *, retry_reason: RetryReason) -> None:
        self.retry_reason = retry_reason
        super().__init__(message)


def compute_etl_retry_eligible_at(attempt_count: int) -> datetime:
    """
    Exponential backoff before the job becomes claimable again.

    Reuses orchestration backoff (base * 2^attempt, cap 1h). ``attempt_count`` is the
    value recorded on the failed claim (1-based after increment in claim()).
    """
    base = settings.job_retry_base_delay_seconds
    exponent = max(attempt_count - 1, 0)
    delay_seconds = min(base * (2**exponent), 3600)
    return datetime.now(UTC) + timedelta(seconds=delay_seconds)


def classify_retry_reason(
    error_message: str,
    exc: BaseException | None = None,
) -> RetryReason:
    if exc is not None and isinstance(exc, EtlRetryableError):
        return exc.retry_reason

    lowered = error_message.lower()
    if "lock timeout" in lowered or "lock_timeout" in lowered:
        return RetryReason.LOCK_TIMEOUT
    if "inventory rebuild busy" in lowered or "inventory_rebuild_busy" in lowered:
        return RetryReason.INVENTORY_REBUILD_BUSY
    if "worker shutdown" in lowered or "shutdown" in lowered:
        return RetryReason.WORKER_SHUTDOWN
    if "старый формат" in lowered or "конвертируйте в .xlsx" in lowered:
        return RetryReason.LEGACY_FILE_TOO_LARGE
    if "visibility timeout" in lowered:
        return RetryReason.VISIBILITY_TIMEOUT
    if "closed transaction" in lowered:
        return RetryReason.SESSION_TRANSACTION
    return RetryReason.GENERIC


def retry_audit_extra(
    *,
    job_id: str,
    attempt_count: int,
    max_attempts: int,
    retry_reason: RetryReason,
    retry_eligible_at: datetime | None = None,
    error_message: str | None = None,
) -> dict[str, object]:
    extra: dict[str, object] = {
        "job_id": job_id,
        "retry_reason": retry_reason.value,
        "attempt": attempt_count,
        "max_attempts": max_attempts,
    }
    if retry_eligible_at is not None:
        extra["retry_eligible_at"] = retry_eligible_at.isoformat()
        extra["retry_delay_seconds"] = max(
            int((retry_eligible_at - datetime.now(UTC)).total_seconds()),
            0,
        )
    if error_message:
        extra["error"] = error_message[:500]
    return extra

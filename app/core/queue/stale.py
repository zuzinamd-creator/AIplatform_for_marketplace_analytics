"""Shared visibility-timeout rules for etl_jobs recovery."""

from __future__ import annotations

from datetime import datetime

from app.models.job import EtlJob


def is_etl_job_stale(job: EtlJob, now: datetime) -> bool:
    """
    A PROCESSING job is stale only when its liveness signal expired.

    Uses last_heartbeat_at when present (worker tick during parse+persist).
    Falls back to claimed_at for jobs that never received a heartbeat.
    """
    timeout = job.visibility_timeout_seconds
    if job.last_heartbeat_at is not None:
        return now.timestamp() > job.last_heartbeat_at.timestamp() + timeout
    if job.claimed_at is not None:
        return now.timestamp() > job.claimed_at.timestamp() + timeout
    return False

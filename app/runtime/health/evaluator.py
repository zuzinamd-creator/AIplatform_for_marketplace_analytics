"""Runtime health evaluation from observability snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.runtime.control_plane.state import RuntimeHealthSeverity
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot


@dataclass(frozen=True)
class HealthDimension:
    name: str
    score: float
    severity: RuntimeHealthSeverity
    detail: str


@dataclass(frozen=True)
class PlatformHealthReport:
    overall_score: float
    overall_severity: RuntimeHealthSeverity
    dimensions: tuple[HealthDimension, ...]
    recommendations: tuple[str, ...]


class RuntimeHealthEvaluator:
    def evaluate(
        self,
        *,
        queue: QueueObservabilitySnapshot,
        rebuild: RebuildQueueObservabilitySnapshot,
        ai_runs_last_hour: int = 0,
        ai_failures_last_hour: int = 0,
    ) -> PlatformHealthReport:
        dims: list[HealthDimension] = []

        queue_score = 100.0
        queue_sev = RuntimeHealthSeverity.OK
        queue_detail = "queue nominal"
        if queue.pending_count > settings.runtime_queue_overload_threshold:
            queue_score = 40.0
            queue_sev = RuntimeHealthSeverity.CRITICAL
            queue_detail = f"queue overload pending={queue.pending_count}"
        elif queue.oldest_pending_lag_seconds and queue.oldest_pending_lag_seconds > settings.ops_queue_lag_warn_seconds:
            queue_score = 65.0
            queue_sev = RuntimeHealthSeverity.WARN
            queue_detail = f"queue lag {queue.oldest_pending_lag_seconds}s"

        dims.append(HealthDimension("queue", queue_score, queue_sev, queue_detail))

        rebuild_score = 100.0
        rebuild_sev = RuntimeHealthSeverity.OK
        rebuild_detail = "rebuild nominal"
        backlog = rebuild.pending_dispatch + rebuild.deferred
        if rebuild.running > settings.runtime_max_concurrent_rebuilds_global:
            rebuild_score = 50.0
            rebuild_sev = RuntimeHealthSeverity.WARN
            rebuild_detail = f"rebuild running={rebuild.running}"
        if backlog > settings.runtime_rebuild_backlog_warn:
            rebuild_score = min(rebuild_score, 55.0)
            rebuild_sev = RuntimeHealthSeverity.WARN
            rebuild_detail = f"rebuild backlog={backlog}"

        dims.append(HealthDimension("rebuild", rebuild_score, rebuild_sev, rebuild_detail))

        ai_score = 100.0
        ai_sev = RuntimeHealthSeverity.OK
        ai_detail = "ai nominal"
        if ai_failures_last_hour > 5:
            ai_score = 60.0
            ai_sev = RuntimeHealthSeverity.WARN
            ai_detail = f"ai failures={ai_failures_last_hour}/h"

        dims.append(HealthDimension("ai_execution", ai_score, ai_sev, ai_detail))

        overall = min(d.score for d in dims)
        severity = max(dims, key=lambda d: _severity_rank(d.severity)).severity
        recs: list[str] = []
        if queue_sev != RuntimeHealthSeverity.OK:
            recs.append("Review ETL worker capacity and queue depth.")
        if rebuild_sev != RuntimeHealthSeverity.OK:
            recs.append("Inspect rebuild backlog and stale RUNNING rows.")
        if ai_sev != RuntimeHealthSeverity.OK:
            recs.append("Check AI provider health and AI_DISABLED_AGENTS.")

        return PlatformHealthReport(
            overall_score=overall,
            overall_severity=severity,
            dimensions=tuple(dims),
            recommendations=tuple(recs),
        )


def _severity_rank(sev: RuntimeHealthSeverity) -> int:
    return {RuntimeHealthSeverity.OK: 0, RuntimeHealthSeverity.WARN: 1, RuntimeHealthSeverity.CRITICAL: 2}[sev]

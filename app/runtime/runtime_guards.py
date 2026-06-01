"""Runtime safety guards (structured logs, no auto-mutation)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.runtime.metrics import emit_runtime_metric
from app.runtime.reliability.circuit_breaker import GLOBAL_CIRCUIT_BREAKERS


@dataclass
class RuntimeGuardState:
    """In-process counters for runaway detection (per orchestrator process)."""

    rebuild_completed_timestamps: deque[datetime] = field(default_factory=deque)
    consecutive_busy_defers: int = 0
    cycles_without_dispatch: int = 0


def record_rebuild_completed(state: RuntimeGuardState) -> None:
    now = datetime.now(UTC)
    state.rebuild_completed_timestamps.append(now)
    cutoff = now - timedelta(hours=1)
    while state.rebuild_completed_timestamps and state.rebuild_completed_timestamps[0] < cutoff:
        state.rebuild_completed_timestamps.popleft()

    count = len(state.rebuild_completed_timestamps)
    if count > settings.reliability_rebuild_storm_per_hour:
        GLOBAL_CIRCUIT_BREAKERS.failure("rebuild_dispatch")
        emit_runtime_metric(
            "runtime_rebuild_storm_contained",
            rebuilds_last_hour=count,
            threshold=settings.reliability_rebuild_storm_per_hour,
        )
    if count > settings.orchestrator_runaway_rebuilds_per_hour:
        emit_runtime_metric(
            "runtime_runaway_rebuild_warning",
            rebuilds_last_hour=count,
            threshold=settings.orchestrator_runaway_rebuilds_per_hour,
        )


def record_busy_defer(state: RuntimeGuardState) -> bool:
    state.consecutive_busy_defers += 1
    if state.consecutive_busy_defers >= 10:
        emit_runtime_metric(
            "runtime_lock_contention_storm",
            consecutive_busy_defers=state.consecutive_busy_defers,
        )
        return True
    emit_runtime_metric(
        "runtime_rebuild_lock_busy",
        consecutive_busy_defers=state.consecutive_busy_defers,
    )
    return False


def record_dispatch_success(state: RuntimeGuardState) -> None:
    state.consecutive_busy_defers = 0
    state.cycles_without_dispatch = 0


def record_idle_cycle(state: RuntimeGuardState, *, rebuild_queue_depth: int) -> None:
    state.cycles_without_dispatch += 1
    if state.cycles_without_dispatch >= 60 and rebuild_queue_depth > 0:
        emit_runtime_metric(
            "runtime_rebuild_starvation_suspected",
            idle_cycles=state.cycles_without_dispatch,
            rebuild_queue_depth=rebuild_queue_depth,
        )


def check_queue_overload(*, pending_jobs: int, threshold: int = 500) -> None:
    if pending_jobs > threshold:
        emit_runtime_metric(
            "runtime_queue_overload_warning",
            pending_jobs=pending_jobs,
            threshold=threshold,
        )

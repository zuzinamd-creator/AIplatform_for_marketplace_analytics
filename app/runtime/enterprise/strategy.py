"""Runtime strategy layer — adaptive orchestration and fairness."""

from __future__ import annotations

from dataclasses import dataclass

from app.runtime.enterprise.dto import OperationalForecastDTO
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot
from app.runtime.policy.engine import RuntimeOperationalPolicy


@dataclass(frozen=True)
class RuntimeStrategyAdvice:
    dispatch_batch_size: int
    fairness_note: str
    rebuild_schedule_bias: float
    throttle_dispatch: bool


class RuntimeStrategyLayer:
    """Adaptive policies derived from forecasts (deterministic)."""

    def advise(
        self,
        *,
        forecast: OperationalForecastDTO,
        queue: QueueObservabilitySnapshot,
        rebuild: RebuildQueueObservabilitySnapshot,
        policy: RuntimeOperationalPolicy,
    ) -> RuntimeStrategyAdvice:
        batch = policy.dispatch_batch_size
        throttle = policy.should_throttle_dispatch(
            queue_pending=queue.pending_count,
            rebuild_backlog=rebuild.pending_dispatch + rebuild.deferred,
        )
        if float(forecast.overload_risk) >= 70:
            batch = max(1, batch // 2)
        bias = 1.0
        if rebuild.pending_dispatch > rebuild.running * 2:
            bias = 1.2
        note = "starvation-aware prioritizer active"
        if throttle:
            note = "dispatch throttled under backlog/queue pressure"
        return RuntimeStrategyAdvice(
            dispatch_batch_size=batch,
            fairness_note=note,
            rebuild_schedule_bias=bias,
            throttle_dispatch=throttle,
        )

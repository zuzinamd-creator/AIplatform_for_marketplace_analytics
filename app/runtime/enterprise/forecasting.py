"""Runtime intelligence — deterministic operational forecasting."""

from __future__ import annotations

from decimal import Decimal

from app.runtime.enterprise.dto import OperationalForecastDTO
from app.runtime.health.evaluator import PlatformHealthReport
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot
from app.runtime.policy.engine import RuntimeOperationalPolicy


class RuntimeIntelligenceEngine:
    """Predictive overload and backlog heuristics (advisory, deterministic)."""

    def forecast(
        self,
        *,
        queue: QueueObservabilitySnapshot,
        rebuild: RebuildQueueObservabilitySnapshot,
        health: PlatformHealthReport,
        policy: RuntimeOperationalPolicy,
    ) -> OperationalForecastDTO:
        queue_sat = Decimal(
            str(min(100.0, 100.0 * queue.pending_count / max(1, policy.queue_overload_threshold)))
        )
        rebuild_pressure = Decimal(
            str(
                min(
                    100.0,
                    100.0
                    * (rebuild.pending_dispatch + rebuild.deferred)
                    / max(1, policy.dispatch_batch_size * 5),
                )
            )
        )
        overload_risk = Decimal(
            str(min(100.0, float(queue_sat) * 0.6 + float(rebuild_pressure) * 0.4))
        )
        autonomy_health = Decimal(str(max(0.0, min(100.0, health.overall_score))))
        ai_pressure = Decimal("0")
        if policy.ai_pause_when_overloaded and queue.pending_count > policy.queue_overload_threshold // 2:
            ai_pressure = Decimal(str(min(100.0, float(queue_sat) * 0.8)))
        drift = Decimal("10") if rebuild.failed > 0 else Decimal("0")
        if health.overall_severity.value == "critical":
            drift = Decimal(str(min(100.0, float(drift) + 40.0)))

        recs: list[str] = []
        if overload_risk >= 70:
            recs.append("Predictive overload risk elevated — expect dispatch throttle.")
        if rebuild_pressure >= 60:
            recs.append("Rebuild backlog pressure high — review fairness and defer policies.")
        if rebuild.failed > 3:
            recs.append("Failed rebuild count rising — investigate semantics drift.")

        return OperationalForecastDTO(
            queue_saturation_score=queue_sat,
            rebuild_pressure_score=rebuild_pressure,
            overload_risk=overload_risk,
            autonomy_health_score=autonomy_health,
            ai_execution_pressure=ai_pressure,
            drift_score=drift,
            recommendations=tuple(recs),
        )

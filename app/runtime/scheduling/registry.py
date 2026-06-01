"""Explicit schedule registry for orchestrator loops."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.core.config import settings


class ScheduleKind(StrEnum):
    REBUILD_DISPATCH = "rebuild_dispatch"
    ORCHESTRATION_MAINTENANCE = "orchestration_maintenance"
    AUTONOMY_HEALING = "autonomy_healing"
    HEALTH_EVALUATION = "health_evaluation"
    QUEUE_VISIBILITY = "queue_visibility"
    CONSISTENCY_VERIFICATION = "consistency_verification"
    ANOMALY_AUDIT = "anomaly_audit"
    DLQ_SWEEP = "dlq_sweep"
    STAGING_CLEANUP = "staging_cleanup"
    ENTERPRISE_OPERATIONS = "enterprise_operations"
    OPERATIONAL_FORECAST = "operational_forecast"


@dataclass
class ScheduleTick:
    kind: ScheduleKind
    due_at: datetime
    interval_seconds: float

    @classmethod
    def periodic(
        cls,
        kind: ScheduleKind,
        *,
        interval_seconds: float,
        now: datetime | None = None,
    ) -> ScheduleTick:
        now = now or datetime.now(UTC)
        return cls(kind=kind, due_at=now, interval_seconds=interval_seconds)

    def next(self, *, now: datetime | None = None) -> ScheduleTick:
        now = now or datetime.now(UTC)
        return ScheduleTick(
            kind=self.kind,
            due_at=now + timedelta(seconds=self.interval_seconds),
            interval_seconds=self.interval_seconds,
        )

    def is_due(self, *, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now >= self.due_at


@dataclass
class ScheduleRegistry:
    """In-process schedule state (deterministic, per orchestrator process)."""

    ticks: dict[ScheduleKind, ScheduleTick] = field(default_factory=dict)

    @classmethod
    def default(cls) -> ScheduleRegistry:
        poll = settings.orchestrator_poll_interval_seconds
        maintenance_every = max(1, settings.orchestrator_maintenance_every_cycles)
        return cls(
            ticks={
                ScheduleKind.REBUILD_DISPATCH: ScheduleTick.periodic(
                    ScheduleKind.REBUILD_DISPATCH, interval_seconds=poll
                ),
                ScheduleKind.ORCHESTRATION_MAINTENANCE: ScheduleTick.periodic(
                    ScheduleKind.ORCHESTRATION_MAINTENANCE,
                    interval_seconds=poll * maintenance_every,
                ),
                ScheduleKind.AUTONOMY_HEALING: ScheduleTick.periodic(
                    ScheduleKind.AUTONOMY_HEALING,
                    interval_seconds=poll * maintenance_every,
                ),
                ScheduleKind.HEALTH_EVALUATION: ScheduleTick.periodic(
                    ScheduleKind.HEALTH_EVALUATION,
                    interval_seconds=poll * 6,
                ),
                ScheduleKind.QUEUE_VISIBILITY: ScheduleTick.periodic(
                    ScheduleKind.QUEUE_VISIBILITY, interval_seconds=poll
                ),
                ScheduleKind.ENTERPRISE_OPERATIONS: ScheduleTick.periodic(
                    ScheduleKind.ENTERPRISE_OPERATIONS,
                    interval_seconds=poll * maintenance_every * 2,
                ),
                ScheduleKind.OPERATIONAL_FORECAST: ScheduleTick.periodic(
                    ScheduleKind.OPERATIONAL_FORECAST,
                    interval_seconds=poll * 12,
                ),
            }
        )

    def due_kinds(self, *, now: datetime | None = None) -> list[ScheduleKind]:
        return [kind for kind, tick in self.ticks.items() if tick.is_due(now=now)]

    def advance(self, kind: ScheduleKind, *, now: datetime | None = None) -> None:
        tick = self.ticks[kind]
        self.ticks[kind] = tick.next(now=now)

"""In-process circuit breakers — explicit open/half-open/closed states."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.core.config import settings
from app.runtime.metrics import emit_runtime_metric


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int
    recovery_seconds: int
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: datetime | None = None

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.opened_at is None:
                return False
            elapsed = (datetime.now(UTC) - self.opened_at).total_seconds()
            if elapsed >= self.recovery_seconds:
                self.state = CircuitState.HALF_OPEN
                emit_runtime_metric(
                    "runtime_circuit_half_open",
                    circuit=self.name,
                )
                return True
            return False
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.opened_at = None
            emit_runtime_metric("runtime_circuit_closed", circuit=self.name)

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now(UTC)
            emit_runtime_metric(
                "runtime_circuit_opened",
                circuit=self.name,
                failure_count=self.failure_count,
            )


@dataclass
class CircuitBreakerRegistry:
    """Process-local breaker registry (deterministic, no distributed state)."""

    _breakers: dict[str, CircuitBreaker] = field(default_factory=dict)

    def get(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=settings.reliability_circuit_failure_threshold,
                recovery_seconds=settings.reliability_circuit_recovery_seconds,
            )
        return self._breakers[name]

    def allow(self, name: str) -> bool:
        breaker = self.get(name)
        allowed = breaker.allow_request()
        if not allowed:
            emit_runtime_metric("runtime_circuit_rejected", circuit=name)
        return allowed

    def success(self, name: str) -> None:
        self.get(name).record_success()

    def failure(self, name: str) -> None:
        self.get(name).record_failure()


GLOBAL_CIRCUIT_BREAKERS = CircuitBreakerRegistry()

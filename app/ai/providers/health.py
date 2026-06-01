"""In-process provider health tracking (complements circuit breaker)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock


@dataclass
class ProviderHealthState:
    provider_id: str
    healthy: bool = True
    consecutive_failures: int = 0
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error: str | None = None
    failover_count: int = 0


_lock = Lock()
_states: dict[str, ProviderHealthState] = {}


def _state(provider_id: str) -> ProviderHealthState:
    with _lock:
        if provider_id not in _states:
            _states[provider_id] = ProviderHealthState(provider_id=provider_id)
        return _states[provider_id]


def record_success(provider_id: str) -> None:
    s = _state(provider_id)
    with _lock:
        s.healthy = True
        s.consecutive_failures = 0
        s.last_success_at = datetime.now(UTC)
        s.last_error = None


def record_failure(provider_id: str, error: str) -> None:
    s = _state(provider_id)
    with _lock:
        s.consecutive_failures += 1
        s.last_failure_at = datetime.now(UTC)
        s.last_error = error[:500]
        if s.consecutive_failures >= 3:
            s.healthy = False


def record_failover(from_provider: str, to_provider: str) -> None:
    _state(from_provider)
    t = _state(to_provider)
    with _lock:
        t.failover_count += 1


def snapshot() -> list[dict]:
    with _lock:
        return [
            {
                "provider_id": s.provider_id,
                "healthy": s.healthy,
                "consecutive_failures": s.consecutive_failures,
                "last_success_at": s.last_success_at.isoformat() if s.last_success_at else None,
                "last_failure_at": s.last_failure_at.isoformat() if s.last_failure_at else None,
                "last_error": s.last_error,
                "failover_count": s.failover_count,
            }
            for s in _states.values()
        ]


def reset_for_tests() -> None:
    with _lock:
        _states.clear()

"""Unit tests for circuit breaker."""

from __future__ import annotations

from app.runtime.reliability.circuit_breaker import CircuitBreaker, CircuitState


def test_circuit_opens_after_threshold() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=3, recovery_seconds=60)
    assert breaker.allow_request() is True
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_circuit_closes_after_success_from_half_open() -> None:
    breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_seconds=0)
    breaker.record_failure()
    assert breaker.allow_request() is True
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED

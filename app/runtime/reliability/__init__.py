"""Production reliability layer — circuit breakers, kill switches, degradation."""

from app.runtime.reliability.circuit_breaker import CircuitBreakerRegistry, CircuitState
from app.runtime.reliability.degradation import DegradationLevel, assess_platform_degradation
from app.runtime.reliability.kill_switches import KillSwitchDecision, RuntimeKillSwitches

__all__ = [
    "CircuitBreakerRegistry",
    "CircuitState",
    "DegradationLevel",
    "KillSwitchDecision",
    "RuntimeKillSwitches",
    "assess_platform_degradation",
]

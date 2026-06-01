# Autonomous Operations

Phase C adds `AutonomousOperationsEngine` (`app/runtime/enterprise/coordinator.py`) — a semi-autonomous enterprise operations cycle.

## Cycle

1. Collect queue/rebuild metrics and health
2. `RuntimeIntelligenceEngine` — deterministic forecast
3. `RuntimeStrategyLayer` — adaptive dispatch advice
4. `OperationalDecisionEngine` — remediation decisions
5. `RemediationPlanner` + `GovernedRemediationExecutor`
6. `record_autonomous_action` — journal with provenance

## Constraints

- No ledger mutation
- Capped actions per cycle (`RUNTIME_MAX_AUTONOMOUS_ACTIONS_PER_CYCLE`)
- Kill switch: `RUNTIME_AUTONOMY_ENABLED`, safety level via `RUNTIME_AUTONOMY_SAFETY_LEVEL`

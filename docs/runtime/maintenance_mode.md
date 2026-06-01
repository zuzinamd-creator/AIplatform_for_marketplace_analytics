# Maintenance mode

## Activation

Set `MAINTENANCE_MODE=true` in environment and restart API/worker/orchestrator.

## Semantics

`RuntimeKillSwitches` blocks:

- ETL worker job claims
- Rebuild dispatch
- Autonomy healing actions (via maintenance gate)
- AI execution (indirectly via maintenance + overload guards)

Orchestrator process may start but cycles skip dispatch when maintenance active.

## API behavior

API remains up for read-only ops endpoints unless separately disabled. `/health` stays available; `/health/ready` checks DB.

## Deactivation

Set `MAINTENANCE_MODE=false`, restart processes, verify `runtime_degradation_state` returns to `normal`.

## Audit

Startup logs `maintenance_mode` flag. Degradation metric emits `level=maintenance`.

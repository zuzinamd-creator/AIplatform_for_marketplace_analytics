# Scheduling Model

## In-process registry

`ScheduleRegistry` (`app/runtime/scheduling/registry.py`) — poll-aligned ticks per orchestrator process.

## Phase C schedule kinds

| Kind | Handler |
|------|---------|
| `enterprise_operations` | Full autonomous ops cycle |
| `operational_forecast` | Dry-run forecast cycle |
| `dlq_sweep` | DLQ visibility (read-only) |

## Tenant policies

`runtime_schedule_policies` — maintenance windows, blackout periods, fairness weights (RLS per tenant).

`EnterpriseScheduleRegistry.platform_in_blackout()` — platform default blackout (02:00–04:00 UTC).

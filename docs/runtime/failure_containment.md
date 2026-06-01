# Failure containment

## Tenant isolation

`TenantContainmentGuard` persists state in `tenant_containment_states`:

- **THROTTLED** — high pending job count; time-bounded
- **QUARANTINED** — DLQ threshold exceeded; blocks worker claim processing and rebuild dispatch

## Rebuild storm

`RuntimeGuardState` + `GLOBAL_CIRCUIT_BREAKERS` open `rebuild_dispatch` when hourly completions exceed `RELIABILITY_REBUILD_STORM_PER_HOUR`.

## AI runaway

Per-tenant rate limit + platform hourly cap (`RELIABILITY_AI_RUNAWAY_PER_HOUR`). AI paused when queue overloaded if `RUNTIME_AI_PAUSE_WHEN_OVERLOADED=true`.

## Dead-letter escalation

`DeadLetterEscalationPolicy` maps global/tenant DLQ counts to operator recommendations.

## Retry exhaustion

ETL: `max_attempts` → DEAD_LETTER (unchanged). Rebuild: orchestration `max_attempts` + explicit backoff via `TenantRecoveryService`.

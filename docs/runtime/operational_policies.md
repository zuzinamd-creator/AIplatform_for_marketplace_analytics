# Operational policies

Config-driven limits in `RuntimeOperationalPolicy.from_settings()` — no hidden retry loops.

## Dispatch & queue

| Setting | Default | Effect |
|---------|---------|--------|
| `RUNTIME_QUEUE_OVERLOAD_THRESHOLD` | 500 | Throttle rebuild dispatch; health CRITICAL |
| `ORCHESTRATOR_MAX_DISPATCH_PER_CYCLE` | 1 | Bounded dispatch per cycle |
| `ORCHESTRATOR_DISPATCH_BATCH_SIZE` | 5 | Fairness batch + backlog throttle factor |
| `RUNTIME_REBUILD_BACKLOG_WARN` | 50 | Health WARN on rebuild backlog |

## Rebuild

| Setting | Default | Effect |
|---------|---------|--------|
| `RUNTIME_INCREMENTAL_TO_FULL_AFTER_ATTEMPTS` | 3 | Escalate incremental → full |
| `RUNTIME_STARVATION_IDLE_CYCLES` | 60 | Documented; prioritizer uses age boost |
| `ORCHESTRATOR_DEFER_BUSY_SECONDS` | 60 | Advisory lock defer |
| `RECOVERY_STALE_RUNNING_SECONDS` | (see config) | Stale RUNNING reset |

## Autonomy

| Setting | Default | Effect |
|---------|---------|--------|
| `RUNTIME_AUTONOMY_ENABLED` | true | Master switch for `AutonomousHealer` |
| `RUNTIME_MAX_AUTONOMOUS_ACTIONS_PER_CYCLE` | 3 | Cap per orchestrator cycle |
| `RUNTIME_AI_PAUSE_WHEN_OVERLOADED` | true | Enforced in `AIAnalyticsEngine` when queue overloaded |

## Production reliability (Phase A)

| Setting | Default | Effect |
|---------|---------|--------|
| `WORKER_ENABLED` | true | ETL worker master switch |
| `MAINTENANCE_MODE` | false | Platform-wide maintenance gate |
| `RELIABILITY_CIRCUIT_FAILURE_THRESHOLD` | 5 | Circuit breaker opens |
| `RELIABILITY_REBUILD_STORM_PER_HOUR` | 40 | Rebuild storm containment |
| `RELIABILITY_TENANT_QUARANTINE_DLQ_THRESHOLD` | 10 | Tenant quarantine |
| `AI_FAILOVER_PROVIDER` | (empty) | Optional LLM failover |

## Observability

Policies are observable via ops runtime summary and [runtime_event_taxonomy.md](runtime_event_taxonomy.md).

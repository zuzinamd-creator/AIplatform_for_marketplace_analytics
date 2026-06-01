# Controlled autonomy governance

## What runtime may automate (bounded)

| Action | Reversible | Tenant scope |
|--------|------------|--------------|
| Reset stale RUNNING rebuilds | Yes | Global maintenance |
| Defer rebuilds under queue pressure | Yes | Per tenant |
| Recover stuck PROCESSING jobs (sample) | Yes | Per tenant |

Each action: `runtime_autonomy_events` row + `runtime_autonomy_action` metric.

## What requires human approval

- Semantics version promotion / invalidation policy changes
- Manual DLQ replay beyond documented runbooks
- RLS bypass or migration operations
- AI provider / prompt contract changes

## Blast radius limits

- `RUNTIME_MAX_AUTONOMOUS_ACTIONS_PER_CYCLE` caps actions per orchestrator tick.
- No distributed coordination; single orchestrator process assumed.
- Dispatch remains advisory-lock serialized per tenant inventory.

## Kill switches

| Switch | Effect |
|--------|--------|
| `ORCHESTRATOR_ENABLED=false` | No rebuild dispatch |
| `RUNTIME_AUTONOMY_ENABLED=false` | No autonomous healer actions |
| `AI_DISABLED_AGENTS` | AI execution pause (see AI docs) |
| `MAINTENANCE_MODE` | Blocks worker, dispatch, autonomy |
| `WORKER_ENABLED=false` | ETL worker idle |

## Escalation

1. Ops runtime health/summary APIs
2. Structured logs + `runtime_autonomy_events` audit
3. Runbooks in `app/operations/recovery.py` for manual replay

## Rollback

Autonomous defers are reversible by re-queuing requirements. Stale RUNNING reset returns rows to retry-eligible states per `RetrySupervisor` rules.

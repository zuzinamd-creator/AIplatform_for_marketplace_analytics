# Retry model

Two retry domains: **ETL jobs** (`etl_jobs`) and **rebuild orchestration** (`snapshot_rebuild_requirements`).

## ETL job retry (existing)

| Stage | Behavior |
|-------|----------|
| `fail()` | `PENDING` if `attempt_count < max_attempts`, else `DEAD_LETTER` |
| Visibility timeout | `recover_stale()` → requeue or DLQ |
| Manual replay | `TenantRecoveryService.replay_dead_letter_job` |

Log events: `job_failed_will_retry`, `job_dead_lettered`, `queue_stale_jobs_recovered`.

## Orchestration retry

| Mechanism | Detail |
|-----------|--------|
| Backoff | `compute_next_eligible_at(attempt_count)` — exponential, cap 3600s |
| Budget | `max_attempts` per requirement row (default 3) |
| Lock busy | **No attempt consumed** — `mark_deferred_lock_busy` |
| Maintenance | `RetrySupervisor.apply_rebuild_retry_backoff` fills missing `next_eligible_at` |
| Stale running | `reset_stale_running_rebuilds` after `recovery_stale_running_seconds` |

## Retry supervisor (`RetrySupervisor`)

Runs on bounded schedule from orchestrator (not every ETL job):

1. Reset stale `running` orchestration rows (per tenant)
2. Apply missing backoff on deferred/pending rows
3. Emit `runtime_orchestration_poison` for terminal `failed` rows (audit)
4. Sample `recover_stuck_processing_jobs` per tenant (queue hygiene)

Log: `runtime_retry_supervisor_completed`.

## Poison detection

| Type | Signal | Escalation |
|------|--------|------------|
| ETL poison | `attempt_count >= max_attempts` | `dead_letter` + ops API |
| Orchestration poison | `failed` + attempts exhausted | `runtime_orchestration_poison` log + ops `/ops/rebuilds` |
| Repeated lock busy | `runtime_lock_contention_storm` | Operator: serialize rebuilds, off-peak full |

## Guarantees

- **Bounded:** no infinite retry loops in worker/orchestrator code paths
- **Visible:** structured logs + ops read API
- **Auditable:** `last_error`, `attempt_count`, `last_attempted_at` on rows
- **Explicit:** no silent re-enqueue; DLQ replay requires operator flag

## Non-goals

- Automatic DLQ replay without operator action
- Cross-tenant retry batching that mutates ledger

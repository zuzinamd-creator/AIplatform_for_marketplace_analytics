# Queue and orchestration observability

Structured JSON logs only (no Prometheus dependency in-repo).

## ETL queue metrics

Emitted by ETL worker and `collect_global_queue_metrics`:

| Event / field | Meaning |
|---------------|---------|
| `runtime_queue_metrics` | `pending_count`, `processing_count`, `dead_letter_count`, `queue_lag_seconds` |
| `runtime_queue_lag_high` | Oldest pending exceeds `OPS_QUEUE_LAG_WARN_SECONDS` |
| `runtime_queue_overload_warning` | Pending jobs > 500 (configurable threshold in code) |
| `queue_stale_jobs_recovered` | Worker `recover_stale` count |
| `job_claimed` / `job_completed` | Per-job lifecycle |

## Rebuild orchestration metrics

| Event | Meaning |
|-------|---------|
| `runtime_rebuild_queue_metrics` | `rebuild_pending_dispatch`, `rebuild_deferred`, `rebuild_running`, `rebuild_failed` |
| `runtime_rebuild_dispatched` | Dispatch started (mode, priority, attempt) |
| `runtime_rebuild_succeeded` | Terminal success |
| `runtime_rebuild_deferred_busy` | Advisory lock not acquired |
| `runtime_rebuild_failed` | Terminal or retryable failure logged |
| `runtime_rebuild_running_count` | Non-zero running rows (stuck detection hint) |

## Retry and recovery metrics

| Event | Meaning |
|-------|---------|
| `runtime_retry_supervisor_completed` | Maintenance pass summary |
| `runtime_orchestration_poison` | Terminal failed requirement audit |
| `recovery_*` | Explicit recovery actions (see ops metrics catalog) |

## Contention metrics

| Event | Source |
|-------|--------|
| `advisory_lock_contention` | `record_metrics` on `InventoryRebuildBusyError` |
| `runtime_rebuild_lock_busy` | Orchestrator defer path |
| `runtime_lock_contention_storm` | 10+ consecutive busy defers in-process |

## Runtime safety warnings

| Event | Trigger |
|-------|---------|
| `runtime_runaway_rebuild_warning` | > `ORCHESTRATOR_RUNAWAY_REBUILDS_PER_HOUR` per process |
| `runtime_rebuild_starvation_suspected` | Idle cycles with pending queue depth |
| `runtime_tenant_health_warning` | `ProductionSafetyGuards` threshold breached |

## Ops API (read-only)

Prefix `/api/v1/ops` — complements logs for dashboards:

- `/ops/queue` — job counts and rows
- `/ops/rebuilds` — orchestration status
- `/ops/dead-letters` — DLQ inspection

## Operational queries (examples)

- Queue lag: filter `runtime_queue_metrics` for `queue_lag_seconds`
- Stuck rebuilds: `rebuild_running > 0` for > `recovery_stale_running_seconds`
- DLQ rate: delta `dead_letter_count` over interval

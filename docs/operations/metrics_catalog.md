# Metrics catalog

Structured JSON log fields via `app/core/observability/etl_metrics.py` and worker/rebuild loggers. **No Prometheus dependency** in this phase — scrape logs or export later.

## Rebuild metrics

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `rebuild_duration_ms` | float | `track_rebuild` | Wall time for incremental/full rebuild txn |
| `rebuild_full_vs_incremental` | string | `track_rebuild` | `incremental` \| `full` |
| `rebuild_window` | string | `bind_log_context` | Date window label |
| `snapshot_rows_written` | int | `record_metrics` | Upsert/staging row count |
| `bulk_upsert_batch_size` | int | `record_metrics` | Batch size used |
| `stream_chunk_size` | int | `record_metrics` | Stream chunk hint |

**Derived (operational):**

| Metric | Formula / observation |
|--------|----------------------|
| Replay throughput | `ledger_rows / (rebuild_duration_ms/1000)` from benchmark logs |
| Snapshot promote duration | Subset of full rebuild txn (not split yet) |
| WAL amplification | `pg_stat_wal` delta before/after rebuild (benchmark script) |

## Queue metrics

| Field / log event | Description |
|-------------------|-------------|
| `job_claimed` | Worker claimed job (`attempt_count`) |
| `job_completed` | Successful ack |
| `job_failed_will_retry` | fail() → pending |
| `job_dead_lettered` | Terminal failure |
| `queue_stale_jobs_recovered` | `queue_recovered` count in extra |
| `job_heartbeat` | Long job liveness |

**Derived:**

| Metric | Description |
|--------|-------------|
| Queue lag | `now - etl_jobs.created_at` for oldest `pending` (query ops API / SQL) |
| Visibility recovery count | Count `recover_stale` log lines per interval |

## Contention & integrity

| Field | Description |
|-------|-------------|
| `advisory_lock_contention` | Incremented on `InventoryRebuildBusyError` |
| `platform_invariant_violation` | Log-only invariant probe (`invariant_id` in extra) |

## Anomaly & drift

| Observation | Source |
|-------------|--------|
| Anomaly rate | `count(etl_anomalies)` / time window via ops API |
| Drift detection count | `count(snapshot_consistency_checks WHERE NOT is_consistent)` |
| Integrity anomalies | `inventory_integrity_anomalies` count |

## ETL processing

| Field | Description |
|-------|-------------|
| `rows_processed` | Normalized rows |
| `rows_rejected` | Anomaly buffer size at end of process |

## Production safety warnings (`app/operations/safety_guards.py`)

Log-only thresholds (env-configurable). No external alerting integration in this phase.

| Log event | Trigger |
|-----------|---------|
| `ops_rebuild_duration_high` | `rebuild_duration_ms > ops_rebuild_duration_warn_ms` (also from `track_rebuild`) |
| `ops_wal_growth_high` | WAL delta > `ops_wal_bytes_delta_warn` |
| `ops_queue_lag_high` | Oldest `pending` job age > `ops_queue_lag_warn_seconds` |
| `ops_anomaly_explosion` | Anomaly count in window > `ops_anomaly_count_warn` |
| `ops_drift_frequency_high` | Failed drift checks in window > `ops_drift_fail_warn` |

Recovery audit logs: `recovery_stale_running_rebuilds`, `recovery_orphaned_staging_cleanup`, `recovery_stuck_processing_jobs`, `recovery_dead_letter_replay`, `recovery_rebuild_backoff_applied`.

## Standard log context

Always prefer: `user_id`, `job_id`, `report_id`, `operation_stage`, `semantics_version`, `correlation_id`.

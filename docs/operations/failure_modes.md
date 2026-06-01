# Failure mode analysis

Survivability reference for marketplace inventory analytics. Each mode maps to **detection → containment → recovery → blast radius**. Recovery primitives live in `app/operations/recovery.py`; warnings in `app/operations/safety_guards.py`.

## 1. Partial rebuild crash

Process dies after staging write but before `promote_staging_to_live()` commits.

| Phase | Action |
|-------|--------|
| **Detection** | `snapshot_rebuild_requirements.orchestration_status = running` with old `started_at`; live snapshot unchanged; staging rows present (`GET /ops/rebuilds`, staging row counts). Log: `inventory_rebuild_failed`. |
| **Containment** | Advisory xact lock released on connection drop; no partial promote to live. Block new full rebuild for tenant until stale row cleared (orchestration + lock). |
| **Recovery** | `TenantRecoveryService.reset_stale_running_rebuilds()` → `DEFERRED` + backoff; `cleanup_orphaned_staging()` for aged staging; re-run full/incremental rebuild. |
| **Blast radius** | Single tenant; live reads may be stale until rebuild succeeds; no ledger corruption. |

## 2. Advisory lock starvation

Tenant persist/rebuild repeatedly hits `InventoryRebuildBusyError` while another holder runs long rebuild.

| Phase | Action |
|-------|--------|
| **Detection** | `advisory_lock_contention` in metrics/logs; persist latency; ops rebuild `running` for extended period. |
| **Containment** | Try-lock (non-blocking) — callers fail fast, no queue spin. `TenantThrottlePolicy.max_concurrent_rebuilds_per_tenant = 1`. |
| **Recovery** | Wait for running rebuild to finish or reset stale `RUNNING`; defer operator-triggered full rebuilds off-peak. |
| **Blast radius** | Tenant-scoped ingest delay; no cross-tenant lock. |

## 3. Queue visibility corruption

Worker crash after `claim()` without `ack()`/`fail()`; `claimed_at` / heartbeat stale.

| Phase | Action |
|-------|--------|
| **Detection** | Jobs `processing` beyond `visibility_timeout_seconds`; missing `job_completed` logs; ops queue `status_counts`. |
| **Containment** | Worker loop calls `recover_stale()` before each claim (global). Bounded `max_attempts` → `dead_letter`. |
| **Recovery** | Worker `recover_stale()` (preventive); `TenantRecoveryService.recover_stuck_processing_jobs()` (explicit tenant pass). |
| **Blast radius** | Delayed report ETL for affected jobs; duplicate processing prevented by idempotent persist where designed. |

## 4. WAL amplification

Large full promote (delete-all + bulk insert) or many concurrent rebuilds inflate WAL/disk.

| Phase | Action |
|-------|--------|
| **Detection** | `pg_stat_wal` delta; log `ops_wal_growth_high`; disk alerts on managed Postgres. Benchmark script compares before/after. |
| **Containment** | Fairness throttle; one rebuild/tenant; off-peak full rebuilds; pause discretionary full rebuilds. |
| **Recovery** | Serialize tenant rebuilds; run `cleanup_orphaned_staging`; verify archiving/replication on host. |
| **Blast radius** | Cluster I/O (shared disk); all tenants on instance may see slower commits. |

## 5. Semantics mismatch

Ingest on version A while snapshots rebuilt with version B, or disabled version still in flight.

| Phase | Action |
|-------|--------|
| **Detection** | Drift checks fail; `platform_invariant_violation` (semantics); ops semantics-status vs snapshot `semantics_version`. |
| **Containment** | Disable ingest on version (`semantics_lifecycle_versions`); `SemanticsInvalidationService.request_rebuild()`. |
| **Recovery** | Full tenant rebuild at target version; validate replay equivalence; re-enable ingest only after `succeeded` orchestration. |
| **Blast radius** | Tenant analytics wrong until rebuild; finance ledger unaffected (append-only). |

## 6. Anomaly persistence outage

`EtlAnomaly` insert fails (DB/network) while main persist path continues or aborts inconsistently.

| Phase | Action |
|-------|--------|
| **Detection** | `etl_anomalies` count drop vs parser warnings; `ops_anomaly_explosion` inverse (sudden zero); failed txn logs on anomaly path. |
| **Containment** | Anomalies in separate txn from snapshot promote — main ledger/snapshot not silently corrupted by anomaly failure. |
| **Recovery** | Re-process report from raw file (new job); inspect `last_error` on job; ops `/ops/anomalies`. |
| **Blast radius** | Observability gap for tenant; processing may complete without audit trail. |

## 7. Dead-letter accumulation

Jobs exhaust retries → `dead_letter`; rebuild requirements → `failed`.

| Phase | Action |
|-------|--------|
| **Detection** | `GET /ops/dead-letters`; rising `dead_letter` in `status_counts`; orchestration `failed`. |
| **Containment** | Stop auto-requeue (no hidden retries); cap `max_attempts`. |
| **Recovery** | Fix root cause (parser, file, semantics); `TenantRecoveryService.replay_dead_letter_job(..., reset_attempt_counter=True)` when operator acknowledges counter reset. |
| **Blast radius** | Stuck reports for tenant until replayed; no automatic cross-tenant replay. |

## 8. Snapshot drift explosion

Many `snapshot_consistency_checks` with `is_consistent=false` or integrity anomalies.

| Phase | Action |
|-------|--------|
| **Detection** | Ops drift-checks; log `ops_drift_frequency_high`; integrity anomaly tables. |
| **Containment** | Pause semantics changes; avoid hand-editing snapshots. |
| **Recovery** | Full rebuild if ledger trusted; compensating ledger import if ledger wrong (append-only). |
| **Blast radius** | Wrong stock/KPIs for tenant until consistent; downstream AI context unreliable. |

## Catastrophic (not auto-recoverable)

- **Ledger tampering / truncation** — violates append-only authority; restore from backup + replay from raw.
- **RLS misconfiguration** — cross-tenant data exposure; fix policies + audit access.
- **Promote without staging validation** — prevented by code path; if bypassed manually, full rebuild required.
- **Total region / database loss** — managed Postgres PITR; redeploy workers; replay raw reports.

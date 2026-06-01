# Disaster recovery playbooks

Operator procedures. **Ledger is authoritative** — snapshots and queue state are recoverable.

## Corrupted snapshot recovery

**Symptoms:** Drift checks fail; `inventory_integrity_anomalies`; wrong stock in API.

1. Confirm ledger intact (`inventory_ledger_entries` row counts stable).
2. Run **full tenant rebuild** (below) — do not hand-edit snapshot rows.
3. Re-run drift verification; expect `is_consistent=true`.
4. If drift persists → semantics version mismatch playbook.

## Full tenant rebuild

**When:** Post-semantics migration, promote mismatch, empty/partial snapshot suspicion.

1. Ensure no concurrent rebuild (advisory lock free).
2. Execute `FullInventoryRebuildService.rebuild()` inside `TenantSession` (worker/job path) **or** wait for rebuild queue consumer when deployed.
3. Verify snapshot row counts vs ledger-derived expectation.
4. Monitor WAL; schedule off-peak if >50k ledger rows.

**Ops visibility:** `GET /api/v1/ops/rebuilds?status=running`

## Queue deadlock recovery

**Symptoms:** Jobs stuck `processing`; no worker progress.

1. Verify workers running (`job_claimed` logs).
2. Worker calls `recover_stale()` each loop — if disabled, restore worker code path.
3. For jobs past visibility timeout still `processing`, restart worker (triggers recover) or manual SQL review (last resort).
4. Dead letters: `GET /api/v1/ops/dead-letters` → fix root cause → `requeue()` if attempts remain.

**Do not** delete `etl_jobs` without understanding report linkage.

## Drift recovery

1. `GET /api/v1/ops/drift-checks?consistent_only=false`
2. Read `mismatch_details` / integrity anomalies.
3. If ledger correct → full rebuild.
4. If ledger wrong → new compensating report/import (append-only).

## Semantics rollback

**Not** a data rollback — freeze ingest:

1. Set version `disabled` in `semantics_lifecycle_versions` (migration/seed).
2. Queue rebuild: `SemanticsInvalidationService.request_rebuild()`.
3. Complete rebuild before re-enabling ingest on new version.
4. `GET /api/v1/ops/semantics-status`

## WAL explosion mitigation

**Symptoms:** Disk growth; slow promotes; high `pg_stat_wal` delta.

1. Pause discretionary full rebuilds.
2. Run full rebuild off-peak per tenant.
3. Verify PostgreSQL archiving/replication on managed service.
4. Reduce concurrent tenants rebuilding (fairness throttle).

## Stuck processing recovery

| State | Action |
|-------|--------|
| `pending` + old | Scale workers; check claim errors |
| `processing` + stale `claimed_at` | `recover_stale` / worker restart |
| `dead_letter` | Inspect error; fix; `TenantRecoveryService.replay_dead_letter_job` |
| Rebuild `running` + stuck | `TenantRecoveryService.reset_stale_running_rebuilds()` |

### Explicit recovery API (code)

`TenantRecoveryService` (`app/operations/recovery.py`) — operator/worker invoked, idempotent:

| Method | Purpose |
|--------|---------|
| `reset_stale_running_rebuilds` | Crash mid-rebuild orchestration |
| `cleanup_orphaned_staging` | Aged staging after failed promote |
| `recover_stuck_processing_jobs` | Tenant-scoped visibility recovery |
| `replay_dead_letter_job` | DLQ → `pending` (optional `reset_attempt_counter`) |
| `apply_rebuild_retry_backoff` | Fill `next_eligible_at` on deferred rows |

See [failure_modes.md](failure_modes.md) for detection and blast radius.

## What not to do

- `UPDATE`/`DELETE` on `inventory_ledger_entries`
- Inline full rebuild on API request during semantics change
- Remove `SKIP LOCKED` or advisory try-locks
- Auto-delete live snapshots without rebuild plan

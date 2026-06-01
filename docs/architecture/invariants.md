# Platform System Invariants

Formal architecture contracts for the marketplace analytics platform.  
**Normative:** violating an invariant is a defect, not an undocumented behavior.

**Related:**

- [Invariant → code mapping](./invariant_mapping.md)
- [Validation matrix](./invariant_validation_matrix.md)

---

## 1. Ledger invariants

| ID | Contract |
|----|----------|
| **LED-APPEND-ONLY** | `inventory_ledger_entries` and `financial_ledger_entries` are append-only. Rebuild and snapshot repair **never** `UPDATE` or `DELETE` ledger rows. |
| **LED-SOURCE-ID** | Inventory idempotency is `(report_id, source_row_id, operation_type)`. Re-import of the same logical row must not duplicate movements (`ON CONFLICT DO NOTHING`). |
| **LED-IMMUTABLE-QTY** | `quantity_delta` and monetary amounts are immutable after insert. Corrections arrive as new rows / new reports. |
| **LED-REPLAY-ORDER** | Ledger replay order is deterministic: `sku → warehouse → operation_date → created_at → source_row_id`. |
| **LED-REPLAY-DET** | Given the same ledger contents and semantics versions, snapshot reconstruction yields identical fingerprint maps. |
| **LED-REBUILD-NO-MUTATE** | `FullInventoryRebuildService` and `InventorySnapshotRebuildService` read ledger only; they do not write ledger. |
| **FIN-DECIMAL** | Money in domain and persist uses `Decimal` / `Numeric`; no silent `float` coercion on ledger paths. |

---

## 2. Snapshot invariants

| ID | Contract |
|----|----------|
| **SNAP-UNIQUE-DAY-SKU-WH** | At most one live snapshot per `(user_id, snapshot_date, sku, warehouse_name)` (`uq_warehouse_stock_snapshot_day_sku_wh`). |
| **SNAP-FP-DET** | Snapshot state fingerprints exclude timestamps and are stable across replays (`snapshot_state_fingerprint`). |
| **SNAP-DERIVED** | Live snapshots are derived state; safe to delete and rebuild from ledger within a window or entirely (full rebuild). |
| **SNAP-PROMOTE-ATOMIC** | Full rebuild promote is one transaction: staging bulk load → `DELETE` all tenant live rows → `INSERT … SELECT` from staging → commit. |
| **SNAP-VIS-NO-PARTIAL** | Readers outside the promote transaction never observe an empty live table or a mix of old deleted rows and incomplete new rows (PostgreSQL MVCC). |
| **SNAP-INCR-WINDOW** | Incremental rebuild deletes only `[rebuild_from … rebuild_to]` and uses carry-forward openings from snapshots strictly before `rebuild_from`. |
| **SNAP-FULL-EQ-INCR** | Full ledger replay and incremental replay with a full window + clean carry-forward produce equivalent fingerprints (see unit/integration proofs). |

---

## 3. Queue invariants

| ID | Contract |
|----|----------|
| **Q-STATE-SOT** | `etl_jobs.status` is the processing lifecycle source of truth; API report status is projected from latest job. |
| **Q-CLAIM-EXCL** | `claim()` selects only `PENDING` rows, uses `FOR UPDATE SKIP LOCKED`, sets `PROCESSING` before commit — at most one worker owns a job. |
| **Q-NO-DUP-PROC** | A job in `PROCESSING` cannot be claimed again until returned to `PENDING` or terminal state. |
| **Q-ACK-TERM** | Successful processing ends in `COMPLETED` with `claimed_at` cleared. |
| **Q-RETRY-BOUND** | `fail()` returns to `PENDING` only when `attempt_count < max_attempts`; otherwise `DEAD_LETTER` (or `FAILED` edge path). |
| **Q-VIS-RECOVER** | `recover_stale()` requeues `PROCESSING` jobs when claim or heartbeat exceeded `visibility_timeout_seconds`, bounded by `max_attempts`. |
| **Q-IDEMP-ENQUEUE** | Active duplicate enqueue `(user_id, idempotency_key)` while `PENDING`/`PROCESSING` returns existing job, not a second row. |
| **Q-BROKER-RLS** | Queue broker uses `QueueSession` (`app.queue_role`); business tables use `TenantSession`. |

---

## 4. Semantics invariants

| ID | Contract |
|----|----------|
| **SEM-NO-SILENT-FALLBACK** | Unknown or disabled semantics versions raise `UnsupportedSemanticsVersionError`; registry lookup does not default to “current parser”. |
| **SEM-INGEST-GATE** | New ingest runs `assert_ingest_allowed(SEMANTICS_VERSION)` before parsing. |
| **SEM-REBUILD-GATE** | Replay classifies each row with `SEMANTICS_REGISTRY[row.semantics_version]` after `assert_rebuild_allowed`. |
| **SEM-FROZEN-ON-ROW** | `semantics_version` is stored on ledger and snapshot rows at persist time. |
| **SEM-INVALID-NO-INLINE** | Semantics invalidation queues `snapshot_rebuild_requirements`; it does **not** run rebuild inline on the request path. |
| **SEM-LIFECYCLE** | Lifecycle (`active` / `deprecated` / `disabled`) is enforced via `governance_policy` (+ optional DB overlay). |

---

## 5. Operational invariants

| ID | Contract |
|----|----------|
| **OPS-LOCK-FAILFAST** | Inventory rebuild uses `pg_try_advisory_xact_lock` per tenant; contention raises `InventoryRebuildBusyError` (no blocking wait). |
| **OPS-LOCK-XACT** | Advisory lock is transaction-scoped; released on commit/rollback. |
| **OPS-ANOMALY-ISOLATED** | ETL anomaly persistence runs in a **separate** transaction after ledger persist; failures must not roll back ledger. |
| **OPS-ANOMALY-BEST-EFFORT** | Anomaly persist is best-effort (`persist_best_effort`); errors are logged, not propagated to fail the job after successful ledger write. |
| **OPS-REBUILD-IDEMP** | Repeated full rebuild on unchanged ledger yields identical snapshot fingerprints. |
| **OPS-DRIFT-READONLY** | `InventoryConsistencyVerificationService` records checks/anomalies; it does not mutate ledger or auto-repair live snapshots. |
| **OPS-CPU-NO-TXN** | Worker runs `process_content` outside a DB transaction; persist + ack in one tenant transaction. |

---

## 6. Multi-tenant invariants

| ID | Contract |
|----|----------|
| **TEN-RLS** | Tenant data rows include `user_id`; RLS policies require `app.current_user_id` or controlled roles. |
| **TEN-LOCK-SCOPE** | Advisory rebuild lock key is derived from `user_id`; tenants do not block each other. |
| **TEN-ANOMALY-SCOPE** | `etl_anomalies`, integrity anomalies, and consistency checks are tenant-scoped. |
| **TEN-NO-BYPASS** | Runtime API/worker paths do not set `app.bypass_rls` except `SystemSession` for migrations. |

---

## 7. Testing invariants

| ID | Contract |
|----|----------|
| **TST-ISOLATE-DB** | Integration tests truncate tenant/queue tables before and after each test (`db_isolation.py`). |
| **TST-UNIQUE-IDS** | Tests use fresh `uuid4()` identities; no shared static tenants across tests. |
| **TST-DET-FIXTURES** | CSV/ledger fixtures are delimiter-safe and deterministic (comma CSV; synthetic scale specs). |
| **TST-REPLAY-EQ** | Full vs incremental rebuild equivalence and fingerprint stability must remain covered when changing rebuild code. |
| **TST-NO-ORDER** | Integration suite must pass under random test order. |
| **TST-GATE** | Integration/stress tests require explicit env gates (`RUN_INTEGRATION_TESTS`, `RUN_STRESS_TESTS`). |

---

## Runtime probes (non-normative helpers)

`app/core/invariants/checks.py` emits structured `platform_invariant_violation` warnings for:

- duplicate snapshot keys in a draft batch
- negative unit rollups in drafts
- unknown semantics versions in drafts
- staging vs live row count mismatch after promote

These **do not** replace contracts above; they aid operations and do not abort transactions.

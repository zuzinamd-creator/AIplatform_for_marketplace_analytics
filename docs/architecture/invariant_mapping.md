# Invariant → Code Mapping

Maps each formal invariant ([invariants.md](./invariants.md)) to enforcement locations and tests.

Legend: **DB** = constraint/policy, **Code** = application logic, **Test** = automated proof.

---

## 1. Ledger

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| LED-APPEND-ONLY | **Code:** no update/delete paths on ledger services; **DB:** no application triggers that mutate ledger | `test_inventory_idempotency.py`, persist uses insert-only |
| LED-SOURCE-ID | **DB:** `uq_inventory_ledger_report_source_operation`; **Code:** `WbFinancialPersistService._persist_inventory_ledger` `ON CONFLICT DO NOTHING` | `test_inventory_idempotency.py`, `test_wb_weekly_report_pipeline.py` |
| LED-IMMUTABLE-QTY | **Code:** ORM models have no update helpers for ledger | Convention + review |
| LED-REPLAY-ORDER | **Code:** `InventoryLedgerStreamingService.stream_grouped_by_key` | `test_inventory_rebuild_benchmark.py` (row counts per group) |
| LED-REPLAY-DET | **Code:** `InventorySnapshotPipeline`, `snapshot_fingerprint` | `test_snapshot_fingerprint.py`, `test_full_incremental_rebuild_equivalence.py`, `test_inventory_rebuild_benchmark.py` |
| LED-REBUILD-NO-MUTATE | **Code:** `FullInventoryRebuildService`, `InventorySnapshotRebuildService` | Code review; rebuild tests never assert ledger mutation |
| FIN-DECIMAL | **Code:** domain types, SQLAlchemy `Numeric` | `test_reconciliation.py`, `test_inventory_reconstruction.py` |

---

## 2. Snapshots

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| SNAP-UNIQUE-DAY-SKU-WH | **DB:** `uq_warehouse_stock_snapshot_day_sku_wh`; **Runtime:** `check_snapshot_draft_batch` → `SNAP-UNIQUE-DAY-SKU-WH` log | `test_inventory_snapshots.py`; unit: `test_platform_invariants.py` |
| SNAP-FP-DET | **Code:** `app/domain/inventory/snapshot_fingerprint.py` | `test_snapshot_fingerprint.py` |
| SNAP-DERIVED | **Code:** `InventorySnapshotStore.delete_window` / `delete_all` | `test_inventory_snapshots.py` |
| SNAP-PROMOTE-ATOMIC | **Code:** `InventorySnapshotStore.promote_staging_to_live` + caller txn | `test_rebuild_production_guarantees.py` (`test_promote_visibility_*`) |
| SNAP-VIS-NO-PARTIAL | **Code:** single txn promote; **DB:** MVCC | `test_rebuild_production_guarantees.py` |
| SNAP-INCR-WINDOW | **Code:** `compute_rebuild_window`, `load_carry_forward_openings` | `test_inventory_rebuild_window.py` (unit) |
| SNAP-FULL-EQ-INCR | **Code:** incremental vs full compute paths | `test_full_incremental_rebuild_equivalence.py`, `test_inventory_rebuild_benchmark.py` |
| SNAP-PROMOTE-ROW-MATCH | **Runtime:** `check_promote_staging_row_match` | Unit: `test_platform_invariants.py` |

---

## 3. Queue

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| Q-STATE-SOT | **Code:** `EtlJob.status`; **Code:** `report_projection.py` | `test_report_projection.py` |
| Q-CLAIM-EXCL | **Code:** `PostgresQueueBackend.claim` `SKIP LOCKED` + status flip | `test_queue_lifecycle.py` (`test_concurrent_claim_*`) |
| Q-NO-DUP-PROC | **Code:** claim filters `PENDING` only | `test_queue_lifecycle.py` |
| Q-ACK-TERM | **Code:** `PostgresQueueBackend.ack` | `test_queue_backend.py`, `test_queue_lifecycle.py` |
| Q-RETRY-BOUND | **Code:** `PostgresQueueBackend.fail` | `test_queue_lifecycle.py` (`test_fail_retry_*`) |
| Q-VIS-RECOVER | **Code:** `recover_stale` | `test_queue_lifecycle.py` (visibility tests) |
| Q-IDEMP-ENQUEUE | **Code:** `PostgresQueueBackend.enqueue` | `test_queue_lifecycle.py` |
| Q-BROKER-RLS | **Code:** `QueueSession` vs `TenantSession` | `app/core/security_context.py`; integration implicit |

---

## 4. Semantics

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| SEM-NO-SILENT-FALLBACK | **Code:** `SEMANTICS_REGISTRY` + `UnsupportedSemanticsVersionError` | `test_semantics_governance_policy.py`, `test_inventory_semantics_versioning.py` |
| SEM-INGEST-GATE | **Code:** `assert_ingest_allowed` in `WbFinancialProcessor.process` | `test_semantics_governance_policy.py` |
| SEM-REBUILD-GATE | **Code:** `assert_rebuild_allowed` in registry resolver | `test_semantics_governance_replay.py` |
| SEM-FROZEN-ON-ROW | **Code:** persist writes `semantics_version` on ledger/snapshots | `test_inventory_semantics_versioning.py` |
| SEM-INVALID-NO-INLINE | **Code:** `SemanticsInvalidationService.request_rebuild` | `test_semantics_governance_replay.py`; code review |
| SEM-LIFECYCLE | **Code:** `governance_policy.py`; **DB:** `semantics_lifecycle_versions` | `test_semantics_governance_policy.py` |
| SEM-UNKNOWN-VERSION-DRAFT | **Runtime:** `check_snapshot_draft_batch` log | `test_platform_invariants.py` |

---

## 5. Operational

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| OPS-LOCK-FAILFAST | **Code:** `acquire_inventory_rebuild_lock` `pg_try_advisory_xact_lock` | `test_inventory_rebuild_locking.py`, `test_rebuild_production_guarantees.py` |
| OPS-LOCK-XACT | **DB:** `pg_try_advisory_xact_lock` (xact-scoped) | `test_inventory_rebuild_lock.py` (unit) |
| OPS-ANOMALY-ISOLATED | **Code:** `ETLPipeline._persist_etl_anomalies_best_effort` separate txn | `test_etl_anomaly_buffer_persist.py` |
| OPS-ANOMALY-BEST-EFFORT | **Code:** `EtlAnomalyPersistService.persist_best_effort` | `test_etl_anomaly_buffer_persist.py` |
| OPS-REBUILD-IDEMP | **Code:** deterministic pipeline | `test_inventory_rebuild_benchmark.py`, `test_rebuild_production_guarantees.py` |
| OPS-DRIFT-READONLY | **Code:** `InventoryConsistencyVerificationService` | `test_rebuild_production_guarantees.py` (`test_drift_*`), `test_inventory_hardening.py` |
| OPS-CPU-NO-TXN | **Code:** `app/etl/worker.py` `process_content` outside txn | Code review |

---

## 6. Multi-tenant

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| TEN-RLS | **DB:** RLS policies on tenant tables; **Code:** `TenantSession` sets `app.current_user_id` | Integration suite under RLS; migrations |
| TEN-LOCK-SCOPE | **Code:** `inventory_rebuild_lock_keys(user_id)` | `test_inventory_rebuild_locking.py` |
| TEN-ANOMALY-SCOPE | **DB:** `user_id` on anomaly tables; **Code:** tenant services | `test_data_quality_validator.py` |
| TEN-NO-BYPASS | **Code:** `SystemSession` only for Alembic | README §12; code review |

---

## 7. Testing

| Invariant | Enforcement | Tests / notes |
|-----------|-------------|---------------|
| TST-ISOLATE-DB | **Code:** `tests/integration/db_isolation.py` autouse | All `tests/integration/*` |
| TST-UNIQUE-IDS | **Convention:** uuid4 in fixtures | `conftest.py`, helpers |
| TST-DET-FIXTURES | **Code:** `wb_fixtures.py`, `inventory_scale_fixtures.py` | Integration + benchmark |
| TST-REPLAY-EQ | **Test:** equivalence suites | See snapshot section |
| TST-NO-ORDER | **CI:** pytest without order dependency | Manual / CI policy |
| TST-GATE | **Code:** `integration_enabled` / `RUN_STRESS_TESTS` fixtures | `tests/integration/conftest.py` |

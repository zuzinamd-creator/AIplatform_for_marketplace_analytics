# AI-assisted change policy

Rules for humans and AI agents modifying this repository. **Goal:** safe evolution without redesigning core algorithms unless explicitly tasked.

## 1. Changes AI MAY perform safely

- Bug fixes that preserve [invariants](invariants.md) and relevant ADRs.
- Additive API fields/schemas (backward compatible).
- New tests mirroring existing patterns (`tests/unit`, `tests/integration` with isolation).
- Documentation, ADR clarifications, log messages, metrics labels.
- Refactors **within** a module that do not change transaction boundaries or ordering.
- New aliases in `FIELD_ALIASES` / operation semantics (non-breaking).
- Log-only invariant probes in `app/core/invariants/`.

## 2. Changes requiring benchmark rerun

Set `RUN_STRESS_TESTS=true` and run:

- `tests/integration/test_inventory_rebuild_benchmark.py`

Required when touching:

- `inventory_ledger_streaming.py`, `inventory_snapshot_compute.py`, `InventorySnapshotPipeline`
- `full_inventory_rebuild.py`, `inventory_snapshot_store.py` (promote path)
- `INSERT_BATCH_SIZE`, bulk insert/promote SQL
- Domain reconstruction/reconciliation hot paths

## 3. Changes requiring integration rerun

`RUN_INTEGRATION_TESTS=true` + full or targeted suite required when touching:

- `postgres_backend.py`, `worker.py`, `security_context.py`
- `inventory_rebuild_lock.py`, rebuild services, RLS migrations
- `persist.py`, `pipeline.py` transaction structure
- `governance_policy.py`, `semantics_registry.py`
- `db_isolation.py`, integration conftest

Minimum targeted suites:

| Area | Tests |
|------|-------|
| Rebuild | `test_rebuild_production_guarantees.py`, `test_inventory_rebuild_locking.py` |
| Queue | `test_queue_lifecycle.py` |
| WB ETL | `test_wb_weekly_report_pipeline.py`, `test_concurrency.py` |

## 4. Changes requiring ADR update

Update or add an ADR when changing **decision-level** behavior in:

- Ledger mutability or idempotency keys
- Advisory lock type, scope, or blocking behavior
- Staging promote algorithm or visibility model
- Replay ordering, fingerprint definition, incremental window rules
- Queue claim/recovery semantics
- Semantics fallback or invalidation flow
- Anomaly transaction isolation

See [ADR index](adr/README.md). Mark superseded ADRs with status and link.

## 5. Forbidden unsafe modifications

**Never** (without explicit architecture approval + ADR):

| Forbidden change | ADR / invariant |
|------------------|-----------------|
| Remove or bypass `pg_try_advisory_xact_lock` | ADR-002 |
| Use blocking `pg_advisory_lock` for rebuild | ADR-002 |
| `UPDATE`/`DELETE` on ledger tables in app code | ADR-001 |
| Promote snapshots outside single transaction | ADR-003 |
| Remove or weaken ledger `ORDER BY` in streaming | ADR-005 |
| Replace `SKIP LOCKED` with plain `FOR UPDATE` on claim | ADR-006 |
| Silent default semantics version on replay | ADR-007 |
| Inline full rebuild on semantics invalidation API path | ADR-007 |
| Persist anomalies in same transaction as ledger | ADR-008 |
| `set_bypass_rls_context` in API/worker business paths | TEN-NO-BYPASS |
| `float` for money in domain/persist | FIN-DECIMAL |
| Auto-repair live snapshots in drift verification | OPS-DRIFT-READONLY |

## Review expectations

Before submitting AI-generated PRs:

1. Run [review_checklist.md](review_checklist.md).
2. Run `python scripts/architecture_governance_check.py`.
3. State which ADRs/invariants were considered in PR description.

# Engineering standards

Pragmatic rules for this codebase. Not a framework — conventions enforced by review, tests, and light scripts.

## Service complexity

- **Target:** orchestration modules ≤ **200 LOC** (excluding imports/docstrings).
- **Grandfathered** (reduce when touched): `app/etl/pipeline.py`, `app/etl/wb/persist.py`, `app/etl/wb/inventory_consistency_verification.py`.
- New logic >200 LOC → extract helper module in same package (e.g. `inventory_snapshot_store.py` pattern).

`python scripts/architecture_governance_check.py` enforces layer imports, required consolidation docs, and warns on LOC / test coverage hints.

Platform structure: [domain_map.md](domain_map.md), [platform_layers.md](platform_layers.md), [dependency_rules.md](dependency_rules.md).

## Module decomposition

- **Domain** (`app/domain`): pure functions, no SQLAlchemy/FastAPI imports.
- **ETL** (`app/etl`): orchestration + I/O; delegate math to domain.
- **Services** (`app/services`): tenant-scoped use-cases; thin wrappers.
- One class per file when the class is the module’s primary export (existing style).

## Observability

- Use `get_logger(__name__)` from `app.core.observability`.
- Include `operation_stage` on ETL/rebuild/queue paths.
- Use `record_metrics` / `track_rebuild` for rebuild and bulk writes.
- Invariant violations: `platform_invariant_violation` via `app/core/invariants`.

## Structured logging

Required keys where applicable: `job_id`, `report_id`, `user_id`, `semantics_version`, `error`.

**Avoid:** logging raw file contents or secrets.

## Migrations

- Alembic only; no manual prod DDL outside migrations.
- Every migration revision must be mentioned in README §18 (Alembic) or changelog note.
- RLS policies must match `TenantSession` / `QueueSession` model.
- Enum changes: use `migrations_support/pg_enum.py` pattern.

## Integration testing

- `@pytest.mark.integration` + `RUN_INTEGRATION_TESTS=true`.
- Autouse `TRUNCATE` isolation (`db_isolation.py`).
- Fresh `uuid4()` per entity; comma-separated CSV fixtures.
- No ordering dependency between tests.

## Benchmark requirements

- Large-scale claims require `test_inventory_rebuild_benchmark.py` with `RUN_STRESS_TESTS=true`.
- Document reference numbers in README only after local run (not invented).

## Replay determinism

- Any change to `ORDER BY`, fingerprint fields, or carry-forward rules requires:
  - `test_snapshot_fingerprint.py`
  - `test_full_incremental_rebuild_equivalence.py`
  - integration rebuild tests if persist path affected

## ADR-governed paths

Changes under these paths should cite ADRs in PR description; governance script warns on git diff:

```
app/core/queue/
app/core/inventory_rebuild_lock.py
app/core/security_context.py
app/etl/wb/full_inventory_rebuild.py
app/etl/wb/inventory_snapshot_rebuild.py
app/etl/wb/inventory_snapshot_store.py
app/etl/wb/inventory_ledger_streaming.py
app/etl/wb/persist.py
app/etl/pipeline.py
app/etl/worker.py
app/domain/semantics/
app/domain/inventory/
app/parsers/wb/semantics_registry.py
alembic/versions/
```

## Forbidden patterns (CI-enforced)

See `scripts/architecture_governance_check.py`:

- Blocking `pg_advisory_lock(` in `app/`
- `set_bypass_rls_context` outside allowlisted files
- `SystemSession` import in `app/api/`

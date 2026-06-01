# Platform boundaries

Formal separation of concerns. Cross-boundary violations require an ADR.

**Consolidation docs:** [domain_map](domain_map.md) · [ownership_model](ownership_model.md) · [platform_layers](platform_layers.md) · [dependency_rules](dependency_rules.md) · [extension_contracts](extension_contracts.md)

## Layer ownership

| Layer | Owns | Must not own |
|-------|------|----------------|
| `app/api` | HTTP, auth, request validation | Money math, ledger rules, rebuild logic |
| `app/schemas` | API DTOs, projections | Business computation |
| `app/services` | Tenant orchestration, enqueue | Parser strategies, snapshot algorithms |
| `app/etl` | Worker loop, pipeline routing, persist orchestration | Domain formulas (delegate to `app/domain`) |
| `app/domain` | Pure finance/inventory/analytics | SQL, FastAPI, storage I/O |
| `app/parsers` | File → normalized rows | Persist, queue |
| `app/core/queue` | `etl_jobs` broker | `reports` business fields |
| `app/models` | ORM mapping | Behavior |

## Transactional boundaries

| Operation | Session | Transaction scope |
|-----------|---------|-------------------|
| API upload + enqueue | `TenantSession` | Report row + job enqueue |
| Worker persist + ack | `TenantSession` | Ledger + snapshots + aggregates + ack |
| Queue claim/recover | `QueueSession` | Single job state transition |
| Full rebuild promote | `TenantSession` | Lock + staging + delete live + insert live |
| Incremental rebuild | `TenantSession` | Lock + window delete + upsert |
| Anomaly persist | `TenantSession` | **Separate** txn after ledger commit |
| Alembic | `SystemSession` | Migrations only |

**Rule:** CPU parsing (`process_content`) runs **outside** any DB transaction.

## Rebuild boundaries

| Component | May touch |
|-----------|-----------|
| `FullInventoryRebuildService` | Staging, live snapshots, advisory lock |
| `InventorySnapshotRebuildService` | Live snapshots (window), advisory lock |
| `InventoryLedgerStreamingService` | Read ledger only |
| `InventoryConsistencyVerificationService` | Read ledger + snapshots; write checks/anomalies only |
| ETL persist | Write ledger; trigger incremental rebuild |

**Forbidden:** rebuild services writing ledger; drift service mutating live snapshots.

## Queue boundaries

- `PostgresQueueBackend` is the only production queue implementation.
- Workers call `recover_stale` before `claim` — not optional in production loop.
- `reports.status` is not authoritative for processing state.

## Observability boundaries

- Structured logs via `app/core/observability` (`get_logger`, `operation_stage`, correlation id).
- Metrics: `record_metrics`, `track_rebuild` on ETL/rebuild paths.
- Platform invariant violations: `platform_invariant_violation` (warnings only).

**Forbidden:** `print()` in production paths; swallowing exceptions without log in worker.

## ETL vs operational layer

| ETL (worker) | Operational (API / ops) |
|--------------|-------------------------|
| Parse file, persist ledger | List reports, costs CRUD |
| Claim/ack jobs | Auth, upload initiation |
| Rebuild snapshots on persist | Queue semantics invalidation **request** only |
| Best-effort anomalies | Read projected status |

## Semantics governance boundaries

- Ingest gates: `WbFinancialProcessor` + `assert_ingest_allowed`.
- Replay gates: `SEMANTICS_REGISTRY` resolver + `assert_rebuild_allowed`.
- Invalidation: `SemanticsInvalidationService` → queue row, **no inline rebuild**.

## Multi-tenant boundary

- All tenant tables: `user_id` + RLS.
- Rebuild lock: per `user_id`, never global.
- Queue role does not grant cross-tenant reads.

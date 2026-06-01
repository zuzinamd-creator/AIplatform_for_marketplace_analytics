# Ownership model

Who owns truth, who may mutate it, and who may only read or derive.

## Authority tiers

| Tier | Meaning | Examples |
|------|---------|----------|
| **Authoritative** | Source of truth; append-only or registry-controlled | Ledgers, `raw_reports`, `semantics_lifecycle_versions` |
| **Derived** | Rebuildable from authoritative data | `warehouse_stock_snapshots`, aggregates, staging |
| **Orchestration** | Coordinates work; not business truth | `etl_jobs`, `snapshot_rebuild_requirements` |
| **Observability** | Audit / ops visibility | `etl_anomalies`, `snapshot_consistency_checks` |
| **Projection** | API read models | Report status from latest job |

## Authoritative sources of truth

| Data | Table / store | Owner module | Mutation allowed by |
|------|---------------|--------------|---------------------|
| Raw report bytes | Object storage + `raw_reports` | Ingest / `report_service` | Upload path only (new version per file) |
| Report metadata | `reports` | `report_service` | API upload, ETL completion updates |
| Financial movements | `financial_ledger_entries` | `etl/wb/persist` | Worker persist txn (insert only) |
| Inventory movements | `inventory_ledger_entries` | `etl/wb/persist` | Worker persist txn (insert only) |
| Semantics registry | `semantics_lifecycle_versions` | Migrations / admin seed | Alembic, explicit governance service |
| Job lifecycle | `etl_jobs` | `PostgresQueueBackend` | QueueSession claim/ack/fail/recover |
| User identity | `users` | `auth_service` | Registration, admin |

**Immutable by policy:** ledger rows (LED-APPEND-ONLY). Corrections = new report / new rows.

## Derived state lifecycle

| Derived artifact | Built by | Invalidated when | Rebuilt by |
|------------------|----------|------------------|------------|
| Live snapshots | Incremental/full rebuild | Ledger append, semantics change, drift | Rebuild services + advisory lock |
| Staging snapshots | Full rebuild | Promote success (swapped) or cleanup recovery | `FullInventoryRebuildService` |
| Daily aggregates | Persist path | New ledger days | Persist / backfill jobs |
| Analytics DTO | Domain + dto | Underlying aggregates/snapshots | Read-time assembly |
| Rebuild queue rows | `SemanticsInvalidationService` | Successful rebuild | Future worker / manual |

**Rule:** never “patch” derived tables to fix ledger mistakes — fix upstream or rebuild.

## Module ownership

| Module | Role | May mutate DB |
|--------|------|---------------|
| `app/api/*` | HTTP, validation | Via services only (tenant tables) |
| `app/services/*` | Tenant orchestration | Yes (tenant scope) |
| `app/etl/worker` | Job loop entry | Indirect via persist/queue |
| `app/etl/pipeline` | Route marketplace ETL | Yes (orchestrated txn) |
| `app/etl/wb/persist` | WB commit path | Yes (ledger + derived) |
| `app/etl/wb/*rebuild*` | Snapshot rebuild | Snapshots/staging/checks only |
| `app/domain/*` | Pure logic | **No** |
| `app/parsers/*` | Parse files | **No** |
| `app/core/queue` | Broker | `etl_jobs` only |
| `app/operations/recovery` | Explicit recovery | Yes (orchestration, staging, jobs) |
| `app/operations/rebuild_orchestration` | Metadata transitions | Requirements rows |
| `app/services/ops_service` | Read-only ops | **No** (SELECT) |
| `app/api/ops` | HTTP read | **No** |

## Read-only services

| Service | Reads | Writes |
|---------|-------|--------|
| `OpsService` | Ops projections | None |
| `InventoryConsistencyVerificationService` | Ledger + snapshots | Check/anomaly rows only |
| `InventoryLedgerStreamingService` | Ledger | None |
| `ProductionSafetyGuards` | Counts / stats | Logs only |

## Mutation permissions matrix

| Layer | Ledger | Live snapshots | Staging | Queue | Semantics registry |
|-------|--------|----------------|---------|-------|-------------------|
| API | No | No | No | Enqueue only | No |
| Worker persist | Insert | Trigger rebuild | No | Ack/fail | No |
| Full rebuild | No | Promote replace | Write/delete | No | No |
| Incremental rebuild | No | Window upsert/delete | No | No | No |
| Recovery | No | No | Delete aged | Requeue/recover | No |
| Invalidation API | No | No | No | No | Request row only |
| Alembic | Schema only | Schema | Schema | Schema | Seed |

## Orchestration-only (no business formulas)

- `app/etl/worker.py` — claim, call pipeline, recover_stale
- `app/etl/pipeline.py` — marketplace routing
- `app/operations/rebuild_orchestration.py` — status metadata
- `app/services/report_service.py` — CRUD + enqueue coordination

## Transaction ownership

See [boundaries.md](boundaries.md). Summary:

- **One owner per business commit:** persist txn owns ledger + snapshot trigger + aggregates.
- **Separate txn:** anomalies (ADR-008).
- **Queue txn:** single job state transition per `QueueSession` begin.
- **Rebuild txn:** advisory lock + snapshot writes in one `TenantSession`.

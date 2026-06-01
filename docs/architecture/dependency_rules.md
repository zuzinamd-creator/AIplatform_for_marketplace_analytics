# Dependency rules

Normative import and access rules. Enforced in part by `scripts/architecture_governance_check.py`.

## Layer dependency matrix

Rows = importer, columns = importee. **Y** = allowed, **N** = forbidden, **W** = warning / legacy only.

| Importer ↓ / Importee → | api | services | etl | domain | parsers | operations | models | core |
|-------------------------|-----|----------|-----|--------|---------|------------|--------|------|
| api | N | Y | W | N | N | N | N | Y |
| services | N | Y | Y | Y | N | N | Y | Y |
| etl | N | N | Y | Y | Y | Y | Y | Y |
| domain | N | N | N | Y | Y | N | W | N |
| parsers | N | N | N | W | Y | N | W | N |
| operations | N | N | N | N | N | Y | Y | Y |
| models | N | N | N | N | N | N | Y | Y |
| core | N | N | N | N | N | N | W | Y |

**W notes:**

- `api` → `etl.*` **removed**; uploads use `app/services/report_upload_service.py` → ETL loaders.
- `domain` / `parsers` → `app.models.*.enums` and row-shaped types (shared kernel).
- `app/domain/inventory/analytics_payload.py` → `app.etl.types.AnalyticsPayload` (legacy; prefer `app/dto` on touch).
- `core/queue` → `app.models.job` only.

## Forbidden imports (hard)

| Source glob | Must not import |
|-------------|-----------------|
| `app/domain/**` | `app.api`, `app.services`, `app.etl`, `app.operations`, `sqlalchemy` |
| `app/parsers/**` | `app.api`, `app.services`, `app.etl`, `sqlalchemy` |
| `app/core/queue/**` | `app.domain`, `app.etl`, `app.services`, `app.api` |
| `app/api/**` | `app.etl.wb`, `app.etl.worker`, `app.etl.pipeline` |
| `app/services/**` | `app.etl.pipeline`, `app.etl.worker` |
| `app/runtime/**` | `app.api` |
| `app/services/ops_service.py` | mutating `app.etl.wb.*rebuild*` |

## Forbidden DB access patterns

| Pattern | Rule |
|---------|------|
| `SystemSession` in API/worker | Migrations only |
| `set_bypass_rls_context` outside allowlist | TEN-NO-BYPASS |
| `QueueSession` reading `reports` | Denormalize on job row |
| Rebuild services writing ledger | LED-REBUILD-NO-MUTATE |
| Ops routes executing recovery | Not exposed; use explicit worker/runbook |
| CPU parse inside `begin()` | Hold transactions short |

## Service-to-service rules

- Services call other services only through established facades (`BaseService` + session).
- Cross-marketplace logic routes through `ETLPipeline`, not ad-hoc imports.
- `SemanticsInvalidationService` may write requirements; must not call `FullInventoryRebuildService`.

## Orchestration entrypoints

| Entrypoint | Allowed callers |
|------------|-----------------|
| `worker.main` / job loop | Process supervisor only |
| `ETLPipeline.run` | Worker, integration tests |
| `TenantRecoveryService.*` | Worker maintenance, operator scripts, tests |
| `RebuildOrchestrationService.mark_*` | Future rebuild worker, tests |
| `get_queue_backend().claim` | Worker loop only |

## Repository boundaries

This codebase uses SQLAlchemy models directly (no separate repository package). Boundaries are:

| Concern | Location |
|---------|----------|
| ORM definitions | `app/models` |
| Queries in orchestration | `app/etl`, `app/services` |
| Pure transforms | `app/domain` |
| Bulk SQL / batch | `app/etl/db_batch`, snapshot store |

**Rule:** new query logic for rebuild belongs in `app/etl/wb`, not `app/api`.

## Transaction ownership

| Transaction | Owner module | Session |
|-------------|--------------|---------|
| Upload + enqueue | `report_service` | `TenantSession` |
| Persist + incremental rebuild | `wb/persist` | `TenantSession` |
| Full promote | `inventory_snapshot_store` | `TenantSession` |
| Claim/ack/fail | `postgres_backend` | `QueueSession` |
| Anomaly flush | `anomaly_persist` | `TenantSession` (separate) |
| Recovery staging delete | `operations/recovery` | `TenantSession` |

## Automated enforcement

```bash
python scripts/architecture_governance_check.py
```

Checks include:

- Forbidden import prefixes per layer
- Blocking advisory lock, RLS bypass misuse
- Required consolidation docs present
- Governed-path test file hints
- LOC warnings, ADR/README git-diff hints

See [engineering_standards.md](engineering_standards.md).

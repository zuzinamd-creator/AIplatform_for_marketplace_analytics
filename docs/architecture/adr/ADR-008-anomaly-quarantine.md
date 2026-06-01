# ADR-008: ETL anomaly quarantine (best-effort, isolated transaction)

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** OPS-ANOMALY-ISOLATED, OPS-ANOMALY-BEST-EFFORT

## Context

Data quality issues (negative qty, missing SKU, etc.) must be recorded without failing successful financial persist or rolling back immutable ledger writes.

## Decision

- Collect anomalies in `EtlAnomalyBuffer` during CPU `process()`.
- After successful ledger persist in tenant transaction, persist anomalies in a **separate** `TenantSession.transaction`.
- `persist_best_effort`: log failures; never propagate to fail completed ETL job.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Same transaction as ledger | Anomaly DB error rolls back ledger (violates ops invariant) |
| Fail entire job on anomaly | Blocks revenue data for quality warnings |
| Silent drop anomalies | No operational visibility |
| Inline fix rows during ETL | Mutates business truth; nondeterministic |

## Tradeoffs

- **Pros:** Ledger durability first; observability second.
- **Cons:** Anomalies may be lost if second txn fails (logged).

## Operational impact

- Monitor `etl_anomaly_persist_failed` logs.
- Dashboards on `etl_anomalies` per tenant.

## Failure scenarios

- Anomaly persist down → ledger still correct; quality blind spot until retry/export.
- Putting anomalies in same txn → ledger rollback on quarantine insert error (forbidden).

## Enforcement

- `ETLPipeline._persist_etl_anomalies_best_effort`, `EtlAnomalyPersistService`
- Tests: `test_etl_anomaly_buffer_persist.py`

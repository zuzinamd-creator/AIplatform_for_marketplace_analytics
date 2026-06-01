# ADR-001: Append-only financial and inventory ledgers

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** LED-APPEND-ONLY, LED-SOURCE-ID, LED-IMMUTABLE-QTY

## Context

Marketplace analytics requires auditable history: corrections arrive as new reports/rows, not silent edits. Snapshots and aggregates are derived and may be rebuilt; ledgers are the source of truth.

## Decision

- `financial_ledger_entries` and `inventory_ledger_entries` are **append-only** in application code.
- Idempotency via `(report_id, source_row_id, operation_type)` with `ON CONFLICT DO NOTHING` for inventory.
- Rebuild services **read** ledger only; they never `UPDATE`/`DELETE` ledger rows.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Upsert ledger rows on re-import | Unsafe: overwrites history; breaks audit and replay determinism |
| Soft-delete ledger | Complicates replay; hidden corrections violate finance audit expectations |
| Rebuild by mutating ledger | Collapses source-of-truth vs derived state; one bug corrupts history permanently |
| Event sourcing without SQL ledger | Higher operational complexity; team already standardized on PostgreSQL RLS model |

## Tradeoffs

- **Pros:** Clear audit trail; deterministic rebuild; simpler drift detection (ledger authoritative).
- **Cons:** Storage growth; corrections need new rows/reports; cannot “fix typo” in place.

## Operational impact

- Disk growth linear with imports; archiving is a business/policy concern, not silent DB edits.
- Support must issue compensating movements, not SQL patches on ledger.

## Failure scenarios

- Manual `UPDATE` on ledger → snapshots diverge from replay; drift checks fire.
- Duplicate `source_row_id` without conflict handling → double-counted stock (mitigated by UNIQUE + DO NOTHING).

## Enforcement

- DB: `uq_inventory_ledger_report_source_operation`
- Code: `WbFinancialPersistService`, no ledger update APIs
- Tests: `test_inventory_idempotency.py`, invariant LED-*

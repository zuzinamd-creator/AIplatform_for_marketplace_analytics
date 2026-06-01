# ADR-006: PostgreSQL queue with SKIP LOCKED claiming

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** Q-CLAIM-EXCL, Q-NO-DUP-PROC, Q-VIS-RECOVER

## Context

ETL runs in multiple worker processes. Job claiming must be exclusive, non-blocking at the database level, and recoverable after worker crashes.

## Decision

- Queue state in `etl_jobs` (not `reports.status`).
- `claim()`: `SELECT … FOR UPDATE SKIP LOCKED` on `PENDING` rows; flip to `PROCESSING` in same transaction under `QueueSession`.
- `recover_stale()` for visibility timeout; bounded retries → `DEAD_LETTER`.
- Broker uses `app.queue_role` RLS context — separate from tenant business writes.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| `SELECT FOR UPDATE` without SKIP LOCKED | Workers block each other; throughput collapse |
| External queue (SQS/Rabbit) only | Loses transactional enqueue with report; another failure domain |
| `UPDATE … RETURNING` race without lock | Duplicate processing under concurrency |
| At-least-once without idempotent persist | Duplicate ledger rows (violates ADR-001) |
| Blocking lock on job row | Head-of-line blocking |

## Tradeoffs

- **Pros:** Native Postgres; simple ops; fits RLS model.
- **Cons:** Polling workers; visibility timeout tuning required.

## Operational impact

- Scale workers horizontally; Postgres handles skip-locked fairness.
- Alert on `PROCESSING` age and DLQ growth.

## Failure scenarios

- Missing `recover_stale` → stuck PROCESSING until timeout.
- Claim without txn → double claim (prevented by `QueueSession.transaction`).

## Enforcement

- `PostgresQueueBackend`
- Tests: `test_queue_lifecycle.py`

# ADR-002: Per-tenant non-blocking advisory locks for inventory rebuild

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** OPS-LOCK-FAILFAST, OPS-LOCK-XACT, TEN-LOCK-SCOPE

## Context

Concurrent ETL persist and snapshot rebuild for the same tenant can interleave deletes/upserts and produce transient or stable corruption. Cross-tenant locking would not scale.

## Decision

- Use `pg_try_advisory_xact_lock(namespace, key)` per `user_id` (namespace `83472933`).
- **Fail fast:** `InventoryRebuildBusyError` on contention — no `pg_advisory_lock` blocking wait.
- Lock is **transaction-scoped** (`xact_lock`): released on commit/rollback.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Blocking `pg_advisory_lock` | Worker/API threads stall; deadlock risk under load; poor UX |
| Row-level lock on snapshots only | Does not serialize full rebuild promote vs incremental window delete |
| Optimistic locking version column | Partial promote visibility; complex client retry across long rebuild |
| No locking | Proven race in concurrent persist + rebuild integration scenarios |
| Application mutex (Redis) | Extra infra; not transactional with PostgreSQL promote |

## Tradeoffs

- **Pros:** Simple; no extra broker; aligns with Postgres txn boundaries.
- **Cons:** Callers must retry on busy; one rebuild per tenant at a time.

## Operational impact

- Monitor `advisory_lock_contention` metric and `InventoryRebuildBusyError` rate.
- Background workers should retry with backoff, not block.

## Failure scenarios

- Ignoring busy error → skipped rebuild; snapshots stale until retry.
- Using session-level advisory lock without release → connection pool pollution (avoided by xact lock).

## Enforcement

- `app/core/inventory_rebuild_lock.py`
- Tests: `test_inventory_rebuild_locking.py`, `test_rebuild_production_guarantees.py`

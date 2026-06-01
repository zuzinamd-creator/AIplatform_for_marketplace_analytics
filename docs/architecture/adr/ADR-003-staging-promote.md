# ADR-003: Full rebuild via staging table and atomic promote

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** SNAP-PROMOTE-ATOMIC, SNAP-VIS-NO-PARTIAL

## Context

Full tenant snapshot rebuild replaces the entire live snapshot set. In-place row-by-row updates expose readers to empty or mixed old/new states.

## Decision

1. Compute snapshots in memory (from streamed ledger).
2. Bulk insert into `warehouse_stock_snapshots_staging` tagged with `rebuild_run_id`.
3. In the **same transaction:** `DELETE` all live tenant snapshots → `INSERT … SELECT` from staging → clear staging → commit.

Readers on READ COMMITTED see prior committed live set or new committed set — never partial promote.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| DELETE live then compute without staging | Long window with **empty** live table |
| Upsert live row-by-row during replay | Partial new/old mix visible; slower |
| Blue/green table swap via rename | Requires DDL locks; migration complexity |
| MVCC-safe without txn | Application crashes mid-delete leave tenant broken |

## Tradeoffs

- **Pros:** Strong visibility story; staging validates row counts before promote.
- **Cons:** Peak WAL/IO on promote; txn duration scales with snapshot row count.

## Operational impact

- Schedule large full rebuilds off-peak; watch WAL (`pg_stat_wal`) on managed Postgres.
- Runtime probe `SNAP-PROMOTE-ROW-MISMATCH` logs count mismatches (non-blocking).

## Failure scenarios

- Promote outside transaction → partial visibility (forbidden by service contract).
- Staging cleared before promote → empty live (prevented by ordering in `FullInventoryRebuildService`).

## Enforcement

- `InventorySnapshotStore.promote_staging_to_live`
- `FullInventoryRebuildService`
- Tests: `test_rebuild_production_guarantees.py`

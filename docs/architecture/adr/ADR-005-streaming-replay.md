# ADR-005: Streaming grouped ledger replay

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** LED-REPLAY-ORDER

## Context

Large tenants may have 50k+ ledger rows. Loading entire ledger into application memory does not scale and risks OOM in workers.

## Decision

- `InventoryLedgerStreamingService` uses SQLAlchemy `stream_results=True` with deterministic `ORDER BY`.
- Yield **one (sku, nm_id, warehouse) group at a time** to `InventorySnapshotComputeService`.
- Incremental path skips pre-window rows only for keys in `carry_forward_keys`.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| `SELECT *` into list | Memory O(ledger rows); benchmark shows unacceptable peak RAM |
| Unordered replay | Nondeterministic snapshots; breaks fingerprints |
| Client-side sort of chunks | Still requires full fetch; CPU + memory cost |
| Key-partitioned parallel workers | Cross-key ordering not needed; adds merge complexity and lock risk |

## Tradeoffs

- **Pros:** Bounded in-flight ledger memory per group; uses PostgreSQL cursor.
- **Cons:** Snapshot draft list still accumulates before bulk insert (O(snapshot rows)).

## Operational impact

- Monitor snapshot row cardinality (SKU × warehouse × days).
- Benchmark documents stream peak RAM vs ledger size.

## Failure scenarios

- Removing `ORDER BY` column → subtle nondeterminism on same-day ties.
- Disabling `stream_results` → memory spike.

## Enforcement

- `app/etl/wb/inventory_ledger_streaming.py`
- Benchmark: `test_inventory_rebuild_benchmark.py`

# Phase 9.17-D — Inventory Rebuild Safety Audit

**Mode:** Audit only · no code · no commits · no deploys  
**Date:** 2026-07-19  
**Depends on:** Phase 9.17-C root-cause findings  
**Question:** Can proposed P0 optimizations preserve inventory correctness?

---

## STEP 1 — Current inventory rebuild logic

### Process scheme

```
earliest_affected_date (from new report movements)
        │
        ▼
compute_rebuild_window
  rebuild_from = earliest_affected
  rebuild_to   = max(latest_snapshot_date, latest_ledger_date)
        │
        ▼
DELETE warehouse_stock_snapshots
  WHERE snapshot_date ∈ [rebuild_from .. rebuild_to]
        │
        ▼
load_carry_forward_openings(rebuild_from)
  → dict[(sku, nm_id, warehouse)] = actual_stock
    from latest snapshot with snapshot_date < rebuild_from
        │
        ▼
stream_grouped_by_key(ALL inventory_ledger_entries for tenant)
  Python skip: if key ∈ carry_forward AND operation_date < rebuild_from → discard
  else keep row, group by (sku, nm_id, warehouse)
        │
        ▼
per key: InventorySnapshotPipeline.rebuild(
            movements,
            rebuild_from, rebuild_to,
            initial_opening = carry_forward.get(key)  # may be None
          )
        │
        ▼
UPSERT warehouse_stock_snapshots for window
```

### Tables & fields

| Table | Role | Key fields used |
|-------|------|-----------------|
| `inventory_ledger_entries` | Source of truth (append-only movements) | `user_id`, `sku`, `nm_id`, `warehouse_name`, `operation_date`, `operation_type`, `quantity_delta`, `cost_per_unit`, `sale_price_per_unit`, `semantics_version`, `created_at`, `source_row_id` |
| `warehouse_stock_snapshots` | Rebuildable projection | `snapshot_date`, `sku`, `nm_id`, `warehouse_name`, `opening_stock`, `inbound/sold/returned/lost/writeoff_units`, `expected_closing_stock`, **`actual_stock`**, discrepancy_* |
| `cost_history` | Valuation for loss analytics | `internal_sku`, `effective_from`, cost components |

### Domain formula (per SKU×warehouse×day)

From `InventoryReconstructionService`:

```
expected_closing = opening + inbound - sold + returned - lost - writeoff
actual_stock     = expected_closing + adjustment_delta
opening[next]    = actual_stock
```

Classification of ledger ops → buckets: `OperationSemanticsStrategyV1.classify_movement`  
(returns, losses, writeoffs, transfers, inventory adjustments all fold into those buckets).

### Code entry points

| Step | Function | File |
|------|----------|------|
| Orchestrate | `InventorySnapshotRebuildService.rebuild` | `inventory_snapshot_rebuild.py` |
| Window | `compute_rebuild_window` | `rebuild_window.py` |
| Carry-forward | `InventorySnapshotStore.load_carry_forward_openings` | `inventory_snapshot_store.py` |
| Stream | `InventoryLedgerStreamingService.stream_grouped_by_key` | `inventory_ledger_streaming.py` |
| Compute | `InventorySnapshotPipeline.rebuild` → `InventoryReconstructionService` | `pipeline.py`, `reconstruction.py` |

### Proven equivalence (already in tests)

- `test_carry_forward_matches_full_history_scan` — window + `initial_opening` ≡ full replay  
- `test_full_replay_matches_incremental_with_clean_carry_forward` — fingerprints match  

**Design intent today is already incremental.** The performance bug is that the SQL layer still loads full history while Python implements the incremental contract.

---

## STEP 2 — Real history dependencies

| Stage | Needs full history? | Needs last state? | Needs last dates? | Evidence |
|-------|---------------------|-------------------|-------------------|----------|
| Window computation | No | Latest snapshot **date** + latest ledger **date** | Yes (bounds) | `compute_rebuild_window`, `_ledger_date_bounds`, `latest_snapshot_date` |
| Delete window | No | No | Dates in range | `delete_window` |
| Carry-forward load | No — only snapshots **before** `rebuild_from` | **Yes: latest `actual_stock` per key** | Latest date per key | `load_carry_forward_openings` |
| Ledger stream (intended) | **Only for keys without carry-forward** | No | Rows with `operation_date >= rebuild_from` for keyed keys | Python skip L56–61 |
| Ledger stream (actual SQL) | **Yes — entire tenant ledger** | — | — | `WHERE user_id = ?` only |
| Day reconstruction in window | No (given correct opening) | Opening stock | Window dates’ movements | `_rebuild_key` + `initial_opening` |
| Reconciliation / loss $ | Window snapshots + costs | Cost as-of date | — | `InventoryReconciliationService` |

**Summary:** Correct incremental rebuild needs:

1. **One number per key:** `actual_stock` at end of day `rebuild_from − 1` (or equivalent), AND  
2. **All ledger movements with `operation_date >= rebuild_from`** for those keys (through `rebuild_to`), AND  
3. **Full movement history** only for keys that **lack** a usable pre-window snapshot.

It does **not** need to re-read pre-window ledger rows for keys that already have carry-forward.

---

## STEP 3 — Carry-forward semantics

### Why ~40k rows are read today

SQL:

```sql
SELECT * FROM inventory_ledger_entries
WHERE user_id = :tenant
ORDER BY sku, warehouse_name, operation_date, created_at, source_row_id
```

There is **no date predicate**. For keys in `carry_forward_keys`, rows with `operation_date < rebuild_from` are skipped **after fetch** in Python. That is why pilot seller (~40 359 rows) pays a full scan to keep ~7 days of work.

### What old periods actually contribute

| Data from before `rebuild_from` | Needed? | How it should arrive |
|---------------------------------|---------|----------------------|
| Net stock position per (sku, nm_id, warehouse) | **Yes** | `actual_stock` of latest snapshot `< rebuild_from` |
| Day-level inbound/sold/return breakdown before window | **No** (not written; window is deleted/rewritten only for ≥ rebuild_from) | Discard |
| Individual sale/return/loss events before window | **No**, if folded into `actual_stock` | Discard |
| Identity of keys that ever existed | **Yes** (to know who needs carry-forward vs full replay) | Snapshot keys + ledger keys in window |

### Returns / storno / adjustments / late ops / transfers

| Case | How handled today | Discard pre-window events? |
|------|-------------------|------------------------------|
| **Returns** | `RETURN` → `returned` bucket on event date | Yes, if before window — net effect in `actual_stock` |
| **Storno / reverse sale** | Typically new ledger rows on their `operation_date` (often as return/adjustment) | Same rule: dated before window → in opening; dated in window → must stream |
| **Inventory adjustment** | `adjustment_delta` on that day → affects `actual_stock` | Pre-window folded into carry-forward |
| **Late operation** (old business day, new file) | `earliest_movement_date` from **this report** sets `rebuild_from` → window expands backward | Events in expanded window **must not** be discarded |
| **Warehouse transfer** | Per-warehouse keys; qty&gt;0 inbound / qty&lt;0 treated as sold-bucket | Pre-window transfers reflected in both warehouses’ `actual_stock`; in-window transfers must be streamed |

**Cannot discard:** any ledger row with `operation_date >= rebuild_from` (including late-dated rows that forced `rebuild_from` earlier).  
**Cannot discard:** carry-forward openings for keys that had activity before the window.  
**Can discard (given valid carry-forward):** ledger rows with `operation_date < rebuild_from` for keys that have a carry-forward opening.

---

## STEP 4 — Safety of `operation_date >= rebuild_from`

### Variant A — Naive filter (all keys)

```sql
WHERE user_id = :u AND operation_date >= :rebuild_from
```

| Scenario | Outcome |
|----------|---------|
| Key has snapshot before window; movements only in window | **Correct** (matches tests) |
| Key has snapshot; also had pre-window history | **Correct** if opening = that snapshot’s `actual_stock` |
| **Key has pre-window ledger history but NO snapshot** (hole, first rebuild, corrupt delete) | **WRONG** — opening becomes 0, stock understated |
| Brand-new SKU first seen in window | **Correct** (opening 0, only window rows) |
| Late ops pulling `rebuild_from` earlier | **Correct** if filter uses the **computed** `rebuild_from` |

**Verdict Variant A: UNSAFE** as a blanket change.

### Variant B — Filter aligned with current Python contract

```text
Keep row if:
  operation_date >= rebuild_from
  OR key ∉ carry_forward_keys   -- still need full history for that key
```

This is exactly what `stream_grouped_by_key` already does after fetch.

| Scenario | Outcome |
|----------|---------|
| Keys with carry-forward | Only window rows needed → **Correct** (proven by unit tests) |
| Keys without carry-forward | Full history still loaded → **Correct** (same as today) |
| Snapshot holes | Still healed by full replay for that key → **Correct** |

**Verdict Variant B: SAFE** (semantic no-op vs current Python; pushes filter to SQL).

### Examples

**SAFE (Variant B):**  
SKU-A has snapshot 2026-07-05 `actual_stock=100`. Rebuild window 07-06..12.  
Stream only movements ≥ 07-06 for SKU-A with `initial_opening=100` → same as full replay.

**UNSAFE (Variant A):**  
SKU-B has ledger from March but snapshots were wiped / never built for March–June.  
`operation_date >= 07-06` + opening 0 → July stock ignores March inbound → **silent corruption**.

---

## STEP 5 — Safety of `DISTINCT ON` latest snapshot

Current Python (`load_carry_forward_openings`):

1. `WHERE snapshot_date < rebuild_from`  
2. `ORDER BY sku, warehouse, nm_id, snapshot_date DESC`  
3. First row per `(sku, nm_id, warehouse)` → `actual_stock`

Equivalent SQL:

```sql
SELECT DISTINCT ON (sku, nm_id, warehouse_name)
  sku, nm_id, warehouse_name, actual_stock
FROM warehouse_stock_snapshots
WHERE user_id = :u AND snapshot_date < :rebuild_from
ORDER BY sku, nm_id, warehouse_name, snapshot_date DESC
```

| Check | Result |
|-------|--------|
| SKU stock opening | Uses same `actual_stock` | OK |
| Per-warehouse stock | Key includes `warehouse_name` | OK |
| nm_id dimension | Key includes `nm_id` (must keep in DISTINCT) | OK |
| Inventory adjustments before window | Already in `actual_stock` | OK |
| Multiple historical days | Only latest kept — **same as today** | OK |
| What we gain | Transfer ~494 keys instead of 7 292 rows (pilot) | Perf |
| What we lose | Nothing vs current semantics | — |

**Verdict: SAFE** (pure equivalent rewrite).  
**Constraint:** DISTINCT key must be `(sku, nm_id, warehouse_name)` — not sku-only.

---

## STEP 6 — Expected effect vs risk

| Optimization | Current (pilot worst / typical) | Expected | Gain | Risk | Complexity |
|--------------|----------------------------------|----------|------|------|------------|
| **1. Date filter Variant B** (SQL = Python contract) | Phase2 111–820 s | **~10–40 s** Phase2 | **High** | **Low** if Variant B; **High** if Variant A | Medium |
| **1b. Naive date filter Variant A** | same | similar speed | High | **High (correctness)** | Low — **do not ship** |
| **2. DISTINCT ON carry-forward** | Load 7 292 snaps | Load ~494 | **Medium** | **Low** | Low |
| **3. Covering sort index** | External merge sort ~1.6 s DB | Ordered index scan | **Low–Medium** alone | **None** (semantic) | Low |

Index alone does **not** fix 820 s wall time; date-bounded fetch does.

---

## STEP 7 — Final conclusions

### 1. Can we safely stop reading the full inventory ledger?

**Yes — conditionally.**  
Only for keys that have a valid carry-forward opening. Keys without openings must still see full history (or an explicit full rebuild path).

Naive “always `operation_date >= rebuild_from`” → **No.**

### 2. Minimal safe optimization

1. **DISTINCT ON** carry-forward (SAFE).  
2. **Covering index** for stream ORDER BY (SAFE).  
3. **SQL date filter Variant B** — encode existing Python skip in SQL (SAFE).

### 3. What can ship immediately (9.17-E candidates)

- DISTINCT ON carry-forward  
- Covering index  
- Optionally Variant B stream filter **with** equivalence tests (full vs incremental vs SQL-filtered) on pilot tenant golden snapshots  

### 4. What needs extra verification before/during implement

- Golden snapshot fingerprint compare: before vs after on production-like pilot data  
- Explicit test: **key with ledger history but zero pre-window snapshots** still full-replays  
- Confirm `earliest_movement_date` always expands window for late-dated rows in new reports  
- Monitor keys/rows still scanned without carry-forward (should be small if snapshots healthy)

### 5. Recommendation for Phase 9.17-E

**Implement package “Safe Incremental Stream v1”:**

1. DISTINCT ON carry-forward  
2. Covering index `(user_id, sku, warehouse_name, operation_date, created_at, source_row_id)` (and/or include `nm_id` if needed for plan)  
3. **Variant B** SQL predicate (not Variant A)  
4. Mandatory regression: existing unit equivalence tests + one integration “hole key” test + pilot fingerprint check  

**Do not** implement naive `operation_date >= rebuild_from` for all keys without the no-carry-forward exception.

---

## One-line safety board

| Proposal | Verdict |
|----------|---------|
| Naive date filter | **UNSAFE** |
| Date filter = current Python contract (Variant B) | **SAFE** |
| DISTINCT ON latest snapshot per key | **SAFE** |
| Covering index | **SAFE** |

---

*Audit only. No code, commits, or deploys in this phase.*

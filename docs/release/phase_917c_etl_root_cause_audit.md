# Phase 9.17-C — ETL Performance Root Cause Audit

**Mode:** Audit only · no code changes · no commits · no deploys  
**Date:** 2026-07-19  
**Evidence:** production `marketplace-worker` logs (2026-07-19) + live Supabase EXPLAIN ANALYZE + table counts for pilot seller `caefecb3-…`

---

## Executive finding (root cause, not symptom)

ETL is slow because **Phase 2 inventory rebuild re-reads the seller’s entire inventory ledger on every report** (SQL has `WHERE user_id = ?` only — **no date filter**), then sorts ~40k wide rows (external disk sort), hydrates ORM objects over the VPS↔Supabase link, and only then applies a **7-day** snapshot window in Python.

Phase 3 aggregate rebuild is **affected-date scoped** (correct), but for dense windows still costs minutes due to Python recompute + purge/upsert over thousands of ledger rows.

AI is not the bottleneck (post–9.17-B1).

---

## STEP 1 — ETL pipeline map

| Stage | Function | File | Tables (R/W) | Input | Output |
|-------|----------|------|--------------|-------|--------|
| Upload | `upload_report` / `buffer_upload_with_checksum` / `validate_report_file` | `app/api/reports.py`, `report_upload_service` | `reports`, storage object | File bytes | Report row `pending` + `etl_jobs` |
| Claim | `queue.claim` / `process_next_job` | `app/etl/worker.py` | `etl_jobs` | Job | Job `processing` |
| Materialize | `materialize_report_file` | `app/etl/report_materialize.py` | Storage GET | `file_path` | Local temp file |
| Parse + Phase 1 | `process_wb_streamed` → `persist_phase1_chunk` | `stream_pipeline.py`, `persist_layers.py` | W: `normalized_report_rows`, `financial_ledger_entries`, `inventory_ledger_entries`, `raw_reports` | XLSX/CSV | Ledger rows for this report |
| Phase 2 Inventory | `InventorySnapshotRebuildService.rebuild` | `inventory_snapshot_rebuild.py` | R: `inventory_ledger_entries`, `cost_history`, `warehouse_stock_snapshots` · W: snapshots (delete window + upsert) | `earliest_affected_date` | Snapshots for rebuild window |
| Phase 2 recon | `_persist_reconciliation` | `persist_layers.py` | `report_reconciliations` | Process result | Reconciliation row |
| Phase 3 Aggregates | `_rebuild_aggregates` | `persist_aggregates.py` | R: `financial_ledger_entries`, `cost_history`, `sku_mapping` · W: `daily_aggregates`, `sku_daily_metrics`, `sku_unit_economics_daily` | Affected dates from report | Day/SKU/unit-econ projections |
| ACK | `ReportService.ack_job` | `report_service` / worker | `etl_jobs`, report derived status | Success | **`processed` — dashboard ready** |
| Post-AI hook | `maybe_generate_recommendation_after_report` | `post_report_ai.py` | AI tables (if enabled) | Report id | **No-op by default (9.17-B1)** |

Phasing code: `WbFinancialPersistService._persist_phases_2_3` in `app/etl/wb/persist.py`.

---

## STEP 2 — Production stage timings

### Sample jobs (complete parse+persist pairs in July logs) — n=3

| Job | Rows | Window | Parse | Phase2 inv (`rebuild_duration_ms`) | Phase3≈ (persist−inv) | Persist total | End-to-end (parse+persist) |
|-----|------|--------|-------|-------------------------------------|------------------------|---------------|----------------------------|
| A `5741bbbd` | 30 | 2026-07-06..12 | 8.3 s | **820.3 s** | 4.6 s | 824.9 s | **833.2 s (~13.9 min)** |
| B `0e5133aa` | 4032 | 2026-07-06..12 | 68.8 s | 111.5 s | **199.3 s** | 310.8 s | **379.7 s (~6.3 min)** |
| C `2a2b1073` (mvp) | 51 | 2026-05-18..24 | 4.1 s | 1.0 s | 2.4 s | 3.5 s | **7.5 s** |

### Aggregate (same 3 jobs)

| Stage | Min | Median | Mean | Max |
|-------|-----|--------|------|-----|
| Parse (`etl_process_content`) | 4.1 s | 8.3 s | 27.1 s | 68.8 s |
| Inventory rebuild | 1.0 s | 111.5 s | 310.9 s | **820.3 s** |
| Persist Phase2+3 (`etl_persist_result`) | 3.5 s | 310.8 s | 379.7 s | **824.9 s** |

### Where minutes go (Job A — worst case)

| Stage | Time | % of pipeline |
|-------|------|---------------|
| Parse + Phase1 | 8.3 s | 1.0% |
| **Phase 2 inventory rebuild** | **820.3 s** | **98.4%** |
| Phase 3 aggregates | 4.6 s | 0.6% |
| ACK / post-AI (legacy on this job) | ~22 s AI | outside dashboard-ready path for KPIs |

### Where minutes go (Job B — large file)

| Stage | Time | % of pipeline |
|-------|------|---------------|
| Parse + Phase1 | 68.8 s | 18.1% |
| Phase 2 inventory | 111.5 s | 29.4% |
| **Phase 3 aggregates** | **199.3 s** | **52.5%** |

**Fact:** Same seller, same 7-day window — Job A dominated by inventory; Job B by aggregates after a denser ledger window. Both can produce **5–14 minute** seller wait.

---

## STEP 3 — Heaviest SQL / operations (TOP-10)

Seller volume (pilot `caefecb3`, live DB 2026-07-19):

| Metric | Value |
|--------|-------|
| `inventory_ledger_entries` | **40 359** |
| Distinct inv (sku, warehouse) keys | 515 |
| `warehouse_stock_snapshots` | 8 025 |
| Snapshots before 2026-07-06 (carry-forward load) | **7 292** |
| Snapshots in window 07-06..12 | 733 |
| `financial_ledger_entries` | 64 540 |
| Fin ledger in window 07-06..12 | **4 804** |
| `sku_daily_metrics` | 2 527 |
| `cost_history` | 98 |

Contrast mvp `c4fcd1f7`: inv 70 · snaps 54 · fin 152 → **7.5 s** total (proves algorithm cost scales with tenant history, not report row count alone).

### TOP-10 expensive operations

| # | Operation | Evidence | Cost class |
|---|-----------|----------|------------|
| 1 | **Full inventory ledger SELECT + ORDER BY** (no date predicate) | `InventoryLedgerStreamingService.stream_grouped_by_key` · EXPLAIN: **40 359 rows**, external merge sort Disk ~14 MB, **1630 ms DB alone**; wall clock in Job A **~820 s** with ORM+network | **Critical** |
| 2 | **Client-side skip of pre-window rows** after full fetch | Skip only in Python when `key in carry_forward_keys` | Amplifies #1 |
| 3 | **Carry-forward loads all historical snapshots** | `load_carry_forward_openings`: 7 292 rows sorted in Python to keep 494 keys · EXPLAIN ~160 ms SQL | High (RAM + network) |
| 4 | Phase 3: load all fin ledger for affected dates | 4 804 rows · index OK (`ix_financial_ledger_user_operation_date`) · SQL ~6 ms · **Python rebuild ~199 s** on Job B | High |
| 5 | Phase 3: purge SKU + unit-econ + daily for dates then upsert | `_purge_*` + `_batch_upsert_*` | High under remote RTT |
| 6 | Parse large XLSX + Phase1 inserts | Job B parse **68.8 s** / 4032 rows | Medium |
| 7 | Full `cost_history` load per rebuild | `_load_cost_snapshots` / `load_cost_snapshots` | Low–Med |
| 8 | Repeated Phase1 row-count asserts (phases 2 & 3) | `_assert_phase1_counts` | Low |
| 9 | Advisory inventory lock | `acquire_inventory_rebuild_lock` | Low unless contended |
| 10 | Upload-time full validation parse | API path before enqueue | Medium (UX, not worker) |

### EXPLAIN highlights (inventory stream)

```
Gather Merge ... rows=40359
  Sort Key: sku NULLS FIRST, warehouse_name NULLS FIRST, operation_date, created_at, source_row_id
  Sort Method: external merge  Disk: 13904kB
  Bitmap Index Scan on ix_inventory_ledger_entries_user_id
Execution Time: 1630.026 ms
```

**Missing covering index for this ORDER BY** → sort spills to disk every rebuild.

Fin window SELECT is healthy (index hit, 5.7 ms). Aggregate slowness is **post-SQL**.

---

## STEP 4 — Full vs incremental recalculation

| Table | Current logic | Recalc volume |
|-------|---------------|---------------|
| `warehouse_stock_snapshots` | **Window rebuild**: delete `[rebuild_from..rebuild_to]`, replay ledger. `rebuild_to = max(latest_snapshot, latest_ledger)` (can extend past report). Labeled `"incremental"` in metrics but stream still reads **full** ledger. | Window days × SKUs written; **read = all tenant inv ledger** |
| `daily_aggregates` | **Affected dates only** — purge dates + rebuild from fin ledger for those dates | A: days in report; **not** full history |
| `sku_daily_metrics` | Same affected dates — purge + rebuild | All SKUs on those dates |
| `sku_unit_economics_daily` | Same affected dates | Same |
| Finance summary / dashboard KPIs | Read projections — **no ETL table rebuild** | N/A |
| `financial_ledger_entries` / `inventory_ledger_entries` | Append-only per report (Phase1) | New report rows only |

**Inventory:** incremental *window write*, **full-history read**.  
**Aggregates:** true **affected-date** rebuild (B not full history).

---

## STEP 5 — Incremental opportunity & expected gain

| Rebuild | Possible approach | Current (pilot worst / typical) | Expected after fix | Est. saving |
|---------|-------------------|----------------------------------|--------------------|-------------|
| Inventory stream | SQL filter `operation_date >= rebuild_from - ε` **or** `DISTINCT ON` carry-forward + stream only window movements | 820 s / 111 s | **10–40 s** typical for 7-day window | **70–95%** on Phase2 |
| Carry-forward | `DISTINCT ON (sku,warehouse) … ORDER BY snapshot_date DESC` for date = rebuild_from−1 | Load 7 292 rows | Load ~494 rows | Large RAM/IO cut |
| Covering sort index | `(user_id, sku, warehouse_name, operation_date, created_at, source_row_id)` | Disk sort 1.6 s+ | Index-only ordered scan | Removes sort spill |
| Phase3 aggregates | Already date-scoped; batch SQL aggregates / fewer round-trips | ~199 s dense window | **20–60 s** | **50–80%** on Phase3 |
| Affected-SKU only | Harder (day totals need all SKUs on date) | — | Limited for daily totals | Low for daily; possible for unit-econ subset |

---

## STEP 6 — Index audit

| Table | Relevant indexes present? | Used by hot query? |
|-------|---------------------------|--------------------|
| `inventory_ledger_entries` | `user_id`, `(user_id, operation_date)`, `(user_id, sku)`, `(user_id, warehouse)` | Stream uses **user_id only** then **filesort** — **sort index MISSING** |
| `warehouse_stock_snapshots` | `(user_id, snapshot_date)`, `(user_id, sku)`, unique day/sku/wh | Carry-forward uses `user_id` + filter date — OK-ish; better as DISTINCT ON |
| `financial_ledger_entries` | **`(user_id, operation_date)`** | Phase3 load — **YES, used** |
| `daily_aggregates` | unique `(user_id, aggregate_date, marketplace)` | Purge/upsert — YES |
| `sku_daily_metrics` | unique `(user_id, sku, metric_date, marketplace)` | Purge/upsert — YES |
| `sku_unit_economics_daily` | `(user_id, metric_date)` + unique | YES |
| `cost_history` | `user_id` | Full tenant load — YES |

### Critically missing

1. **Composite index matching inventory stream ORDER BY**  
   `(user_id, sku, warehouse_name, operation_date, created_at, source_row_id)`
2. **Date predicate in inventory stream SQL** (index alone is insufficient if query still reads all history)
3. Optional: carry-forward optimized query / partial index on latest snapshot per key

---

## STEP 7 — Optimization roadmap

### P0 — quick wins (&lt; 1 day)

| Item | Speedup | Risk | Complexity |
|------|---------|------|------------|
| Add covering sort index for inventory stream | Medium (cut sort spill; alone **not** enough for 820→seconds) | Low | Low |
| SQL `operation_date >= rebuild_from` (with carry-forward openings) | **High (primary)** | Med (must preserve semantics for keys without carry-forward) | Med |
| Carry-forward `DISTINCT ON` / latest-only | Medium | Low | Low |
| Emit separate metrics: `phase2_ms`, `phase3_ms`, ledger rows scanned | Observability | None | Low |

### P1 — medium

| Item | Speedup | Risk | Complexity |
|------|---------|------|------------|
| Push Phase3 aggregation toward SQL `GROUP BY` | High on dense windows | Med (parity tests) | Med–High |
| Reduce Phase1 assert chatter / batch cost loads | Low–Med | Low | Low |
| Parallel Phase2/Phase3 where lock-safe | Med | Med | Med |

### P2 — architectural

| Item | Speedup | Risk | Complexity |
|------|---------|------|------------|
| Incremental inventory delta apply (no window replay) | Very high | High (correctness) | High |
| Projection materialization queue separate from ingest ACK | UX (faster “processed”) | Med (stale reads) | High |
| Co-locate worker with Postgres / read replica for rebuild | Med–High | Ops | Med |

---

## STEP 8 — Final answers

### 1. Why does ETL take 5–14 minutes?

Because for a real seller with **~40k inventory ledger rows** and **~65k financial ledger rows**, each upload triggers:

- Phase 2: **full inventory ledger re-read + sort + ORM stream** to rewrite a **small date window** of snapshots (Job A: **820 s ≈ 98%** of runtime).
- Phase 3: **affected-date** finance rebuild that is correct in scope but still **CPU/ORM/RTT heavy** when the window holds thousands of ledger rows (Job B: **~199 s ≈ 52%**).

Report size (30 vs 4032) is a weak predictor; **tenant history size + window density** dominate.

### 2. Top 3 delay causes

1. **Inventory stream without date filter** (full-table tenant scan every job).  
2. **Remote Supabase + ORM hydration** amplifying that scan (DB sort ~1.6 s ≠ wall ~820 s cold).  
3. **Phase 3 Python purge/rebuild** over dense affected-date ledger (thousands of rows).

### 3. Biggest win

**Stop reading the full inventory ledger:** date-bounded SQL (+ correct carry-forward) → expected **order-of-magnitude** cut on Phase 2 for the pilot seller.

### 4. Minimum realistic time without architecture change

With P0 (date-filtered stream + DISTINCT carry-forward + covering index) on this tenant/window:

- Small/medium reports: **~30–90 s** end-to-end realistic.  
- Large 4k-row parse still ~1 min parse → **~2–3 min** until Phase3 also tightened.

### 5. After full optimization (P0–P2)

- Typical weekly report: **15–45 s** to `processed`.  
- Large multi-thousand-row file: **1–2 min** (parse-bound).  
- Sub-10 s for small reports on warm DB (already seen on mvp: **7.5 s**).

---

## Evidence appendix

| Source | Detail |
|--------|--------|
| Worker logs | Job A `rebuild_duration_ms=820262.97`; Job B `111517.4` + `etl_persist_result=310842.58` |
| Live counts | SLOW inv 40359 / snaps_before 7292 / fin_window 4804 |
| EXPLAIN | Inventory stream external merge; fin window index scan 5.7 ms |
| Code | `inventory_ledger_streaming.py` L35–46; `rebuild_window.py`; `persist_aggregates._rebuild_aggregates` |

**Out of scope for this phase:** implementing fixes, commits, deploys.

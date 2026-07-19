# Phase 9.17-E1 — Production Performance Certification

**Mode:** Measurement only · no code / commit / deploy in E1 itself  
**Date:** 2026-07-19 (UTC)  
**Production SHA:** `f85dea6151cc8b222b4aa794d72fac1939c5f1cd`  
**Alembic:** `0037_inv_stream_idx` · index `ix_inventory_ledger_stream_order` present  
**Tenant:** pilot `caefecb3-5789-4878-a9d4-929be573fbcc`

## Identity

| Item | Value |
|------|-------|
| HEAD / main / release / GitHub / backend | `f85dea6…` |
| Backend / worker restart | 2026-07-19 17:36:37 / 17:36:39 UTC |

## Live samples (after 9.17-E)

| Sample | Report | Rows | Window | Parse | Inventory | phase2_ms | phase3_ms | Total ETL |
|--------|--------|------|--------|-------|-----------|-----------|-----------|-----------|
| C1 fixture | `a207bb2e…` | 51 | 05-18..07-12 | 4.7 s | 35.2 s | 35557 | 2494 | ~44 s |
| **A′** (Job A file) | `a31b3b74…` | 30 | **07-06..12** | 3.2 s | **78.7 s** | **78988** | **2168** | **~86 s** |
| **B′** (Job B file) | `92e9f9be…` | 4032 | **07-06..12** | 40.9 s | **30.8 s** | **31056** | **2441** | **~98 s** |

## vs 9.17-C baseline

| Metric | Before (A / B) | After (A′ / B′) | Change |
|--------|----------------|-----------------|--------|
| Inventory rebuild | 820 s / 112 s | 79 s / 31 s | −90% / −72% |
| Total ETL | ~14 min / ~6 min | ~1.4 min / ~1.6 min | −90% / −74% |

Phase 3 on B′ (~2.4 s vs historical ~199 s) is a warm reprocess of the same window — **not** attributed to 9.17-E (inventory-only).

## Data correctness (A′/B′ window)

- Dashboard KPI / Financial Summary / Top SKU — populated  
- Inventory economics — stock calculated  
- `discrepancy_units ≠ 0` in window — **0** (no snapshot mismatch / drift)  
- Inventory rebuild errors in cert logs — **0**  
- Negative `actual_stock` with `expected=actual` — pre-existing ledger openings; not a rebuild mismatch  

## Verdict

**GO**

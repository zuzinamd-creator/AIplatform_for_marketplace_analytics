# Technical Debt Register — v0.6

**Date:** 2026-06-07  
**Phase:** 6.6.0  
**Review cycle:** Quarterly or before v0.7 planning  
**Policy:** No production AI changes from this register until explicitly scheduled

---

## Summary

| Severity | Count | Trend |
|----------|-------|-------|
| Critical | 0 | — |
| High | 4 | stable |
| Medium | 9 | +2 from 6.5.0 |
| Low | 8 | stable |

---

## Critical

*None at v0.6 pilot-validated scope.*

---

## High

### TD-H01 — Single-seller AI validation

| Field | Value |
|-------|-------|
| **Description** | AI quality gates validated on 1 pilot user (4 reports). Four P0 archetypes have no dataset. |
| **Impact** | Unknown behavior on small/seasonal/unprofitable/no-ads sellers; not blocking pilot client. |
| **Affected** | `app/ai/**`, validation framework |
| **Evidence** | `reports/multi_seller_replay.json` — 1/5 PASS, 4 GAP |
| **Fix** | Onboard sellers per archetype; re-run replay | 
| **Target** | v0.7 or when second client onboarded |

### TD-H02 — Hardcoded AI thresholds

| Field | Value |
|-------|-------|
| **Description** | ~70 thresholds in Python constants (inventory days, IQ +8, revenue ±10%, usefulness ×0.88). |
| **Impact** | Changes require code deploy + manual re-audit; no per-tenant tuning. |
| **Affected** | `priority_engine.py`, `intelligence.py`, `governed_signals.py` |
| **Evidence** | `docs/ai/threshold_catalog.md` |
| **Fix** | Externalize to config module or env-backed registry with audit harness |
| **Target** | v0.7.1 |

### TD-H03 — Business Coverage V1 at 50%

| Field | Value |
|-------|-------|
| **Description** | Four coverage blocks unavailable (Ads, Tax, OPEX, Conversion). |
| **Impact** | AI cannot reason about ad ROI, tax, operational costs; advertising warning always possible. |
| **Affected** | `business_coverage.py`, executive summary |
| **Evidence** | Phase 6.3 blueprint, pilot audit |
| **Fix** | Phase 6.3+ expansion (Ads Intelligence first) |
| **Target** | v0.7 roadmap |

### TD-H04 — Financial KPI read APIs incomplete

| Field | Value |
|-------|-------|
| **Description** | Dashboard revenue/profit/margin/trends lack full read API surface for external MVP. |
| **Impact** | Blocks full analytics product without operator support. |
| **Affected** | `app/api/`, `frontend/` |
| **Evidence** | `docs/product/mvp_readiness.md` |
| **Fix** | Tier 1 roadmap items (Weekly Analysis, period selector) |
| **Target** | v0.7 |

---

## Medium

### TD-M01 — Root CHANGELOG.md stale

| Field | Value |
|-------|-------|
| **Description** | Root `CHANGELOG.md` stops at Phase 5; v0.6 history in `docs/release/CHANGELOG.md` only. |
| **Impact** | Confusion for contributors checking root file. |
| **Fix** | Sync root from docs/release or add pointer line |
| **Target** | v0.6.1 housekeeping |

### TD-M02 — Documentation hub incomplete index

| Field | Value |
|-------|-------|
| **Description** | ~175 markdown files; hub indexes ~35. Runtime/product depth docs unlinked. |
| **Impact** | Discovery friction for new developers. |
| **Fix** | Expand `docs/README.md` sections incrementally |
| **Target** | Ongoing |

### TD-M03 — Trust documentation triplication

| Field | Value |
|-------|-------|
| **Description** | `trust_and_limitations.md`, `trust_and_transparency.md`, `trust_experience.md` overlap. |
| **Impact** | Maintenance drift; unclear canonical source. |
| **Fix** | Merge or cross-link with single canonical doc |
| **Target** | v0.7 docs sprint |

### TD-M04 — Domain layer SQLAlchemy exceptions

| Field | Value |
|-------|-------|
| **Description** | `intelligence.py`, `period_queries.py` import SQLAlchemy under `app/domain/` (allowlisted). |
| **Impact** | Layer purity violation; harder to test domain in isolation. |
| **Fix** | Move query logic to repository layer when touched |
| **Target** | When inventory/report queries next refactored |

### TD-M05 — Phase audit JSON accumulation

| Field | Value |
|-------|-------|
| **Description** | `reports/` holds 6 JSON artifacts (~208 KB); phase 621/622 large historical dumps. |
| **Impact** | Repo noise; evidence chain valuable but unorganized. |
| **Fix** | Archive to `docs/release/audit_artifacts/` with index |
| **Target** | v0.6.1 housekeeping |

### TD-M06 — upload-test tenant without AI recs

| Field | Value |
|-------|-------|
| **Description** | Second DB tenant has ETL data but 0 recommendations — incomplete test asset. |
| **Impact** | Cannot replay seasonal/high-inventory on second seller. |
| **Fix** | Run backfill or mark as ETL-only fixture |
| **Target** | When second client needed |

### TD-M07 — Threshold catalog not enforced in CI

| Field | Value |
|-------|-------|
| **Description** | Catalog is documentation-only; no CI check that code constants match catalog. |
| **Impact** | Drift between docs and code undetected. |
| **Fix** | Script to diff catalog vs grep constants |
| **Target** | v0.7 |

### TD-M08 — Operating Director scaffold unused

| Field | Value |
|-------|-------|
| **Description** | `app/ai/director/` designed but not wired to production pipeline. |
| **Impact** | Dead code surface; confusion about active architecture. |
| **Fix** | Document as experimental; activate or isolate in v0.7 |
| **Target** | v0.7 architecture decision |

### TD-M09 — Frontend dist in workspace

| Field | Value |
|-------|-------|
| **Description** | `frontend/dist/` build output present (gitignored). |
| **Impact** | Local disk; no git pollution if ignore holds. |
| **Fix** | Ensure CI builds fresh; optional cleanup script |
| **Target** | Low priority |

---

## Low

### TD-L01 — Empty `docs/release/go_no_go/` directory

Reserved placeholder from 6.4.1; decisions documented elsewhere.

**Target:** Remove or populate in housekeeping.

### TD-L02 — `docs/PR_P0_ETL_STABILIZATION.md` at docs root

Completed PR notes; should link from hub only.

**Target:** Move to `docs/archive/` when convenient.

### TD-L03 — Root `node_modules/` (minimal)

Small root package.json lock; most deps in `frontend/node_modules`.

**Target:** Consolidate or document purpose.

### TD-L04 — Pre-v0.6 README archive (2923 lines)

`docs/archive/README_pre_v06.md` — valuable but large.

**Target:** Keep; optional section splits deferred.

### TD-L05 — Pilot UUID in README and audit scripts

Intentional transparency; default in scripts accepts `--user-id` override.

**Target:** No change unless multi-tenant audit CI added.

### TD-L06 — pytest warnings (3)

RuntimeWarning in auth audit mock; non-blocking.

**Target:** Clean up mock in test hygiene pass.

### TD-L07 — `docs/analytics/financial_model_mvp.md` missing

Planned in 6.4.1 P2; content in archive.

**Target:** Optional v0.7 doc.

### TD-L08 — Archetype manifest pending user_ids

4/5 archetypes `pending_dataset` in manifest.

**Target:** Update when sellers onboarded (not blocking pilot tag).

---

## Debt explicitly NOT tracked (accepted)

| Item | Rationale |
|------|-----------|
| Multi-archetype PASS for release tag | Out of scope for `v0.6-pilot-validated` |
| External MVP readiness | Not current goal |
| LLM prompt changes | Deterministic MVP by design |
| Ozon full ETL | WB-first pilot client |

---

## Related documents

- [v06_release_manifest.md](v06_release_manifest.md)
- [mvp_hardening_plan.md](mvp_hardening_plan.md)
- [threshold_catalog.md](../ai/threshold_catalog.md)

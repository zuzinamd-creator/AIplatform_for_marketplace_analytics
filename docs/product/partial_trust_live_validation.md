# Partial Trust — Live Validation Procedure (Phase 9.7-D)

**Date:** 2026-07-11  
**Purpose:** Production-safe validation of PARTIAL trust (1–99% COGS coverage) before Phase 9.8 Analytics Hub physical merge.  
**Baseline:** Phase 9.7-D trust closure; reconciliation backend profit gating deployed.

---

## Why this procedure exists

Production currently has validated tenants for **INSUFFICIENT** (`mvp-e2e-test@mail.ru`, 0%) and **FULL** (`margarita.zuzina@mail.ru`, 46/46 = 100%). No production seller has 1–99% coverage. PARTIAL UX is validated via unit tests and code audit only — this procedure closes the live validation gap.

---

## Tenant requirements

| Requirement | Detail |
|-------------|--------|
| Account type | Dedicated staging or pilot seller (not shared MVP E2E tenant) |
| Marketplace | Wildberries (`wildberries`) |
| Finance data | ≥1 WB finance report uploaded and processed for target period |
| Sold SKUs | ≥5 distinct SKUs with sales in period |
| COGS upload | Costs for **subset only** — target 40–60% of sold SKUs |
| Rebuild | Aggregate rebuild completed (worker idle or manual `rebuild_financial_projections`) |
| Period | Fixed 7-day window, e.g. `2026-06-29` → `2026-07-05` (match pilot tenants) |

### Required COGS coverage

| Metric | Target |
|--------|--------|
| `sku_cost_coverage_pct` | **1–99%** (not 0%, not 100%) |
| `profit_metrics_trust` | `"partial"` |
| Covered SKUs | ≥1 and < total sold SKUs in period |

**Example:** 10 sold SKUs, COGS uploaded for 5 → ~50% → PARTIAL.

---

## Pre-validation API checks

Run authenticated requests for the pilot period before browser walkthrough.

### 1. Cost coverage

```
GET /api/v1/analytics/cost-coverage?marketplace=wildberries&start=2026-06-29&end=2026-07-05&limit=50
```

**Expected:**

```json
{
  "summary": {
    "sku_cost_coverage_pct": "50.00",
    "covered_skus": 5,
    "total_skus": 10
  }
}
```

### 2. Revenue KPI integrity

```
GET /api/v1/analytics/kpis/summary?marketplace=wildberries&start=2026-06-29&end=2026-07-05
```

**Expected:**

```json
{
  "kpis": {
    "total_profit": "45000.00",
    "margin_pct": null
  },
  "integrity": {
    "profit_metrics_trust": "partial",
    "sku_cost_coverage_pct": "50.00"
  }
}
```

### 3. Period compare

```
GET /api/v1/analytics/kpis/period-compare?marketplace=wildberries&start=2026-06-29&end=2026-07-05&compare_start=...&compare_end=...
```

**Expected:**

```json
{
  "delta_profit": "1200.00",
  "integrity": { "profit_metrics_trust": "partial" }
}
```

(`delta_profit` numeric when both periods have gated profit; margin delta null.)

### 4. Reconciliation (Phase 9.7-D)

```
GET /api/v1/analytics/reconciliation/period?marketplace=wildberries&start=2026-06-29&end=2026-07-05
```

**Expected:**

```json
{
  "breakdown": {
    "profit": "42000.00"
  },
  "integrity": {
    "profit_metrics_trust": "partial",
    "sku_cost_coverage_pct": "50.00"
  }
}
```

Profit is **non-null** at partial trust (estimate allowed). COGS row shows actual summed COGS (may be understated).

---

## Validation steps (browser)

Use [pilot_trust_validation.md](pilot_trust_validation.md) Scenario B. Moderated session ~45 min.

| Step | Surface | Action | Expected UI |
|------|---------|--------|-------------|
| B1 | Dashboard `/app/dashboard` | Open overview | Banner warn tone; profit `~₽`; margin `—`; chart dashed/null segments |
| B2 | Comparison `/app/analytics/weekly` | Open period compare | Profit Δ `~` warn; margin Δ `н/д`; no strong red profit-decline priority |
| B3 | Economics `/app/economics` | View SKU table | COGS-covered SKU: «Оценка: …»; margin column hidden |
| B4 | SKU Drilldown `/app/economics/sku/:sku` | Open one SKU | Profit `~formatted`; margin hidden |
| B5 | Reconciliation `/app/finance/reconciliation` | View profit KPI | Badge «Оценка»; profit `~₽`; integrity from reconciliation API |
| B6 | Cost Coverage `/app/finance/cost-coverage` | Upload 1 missing SKU COGS | Coverage bar increases; trust may shift toward full |
| B7 | AI Recommendations `/app/ai/recommendations` | View disclosure | «оценочная прибыль» copy; margin hidden note |

---

## Expected API responses by trust state

| Endpoint field | FULL | PARTIAL | INSUFFICIENT |
|----------------|------|---------|--------------|
| `integrity.profit_metrics_trust` | `full` | `partial` | `insufficient` |
| `kpis.total_profit` | numeric | numeric | `null` |
| `kpis.margin_pct` | numeric | `null` | `null` |
| `delta_profit` | numeric | numeric | `null` |
| `breakdown.profit` (reconciliation) | numeric | numeric | `null` |

---

## Expected UI behavior summary

| Element | PARTIAL |
|---------|---------|
| `ProfitTrustBadge` | «Оценка» (warn tone) |
| `formatProfitValue` | `~₽` prefix |
| `formatMarginValue` | `—` |
| `CostTrustBanner` | Visible (inline or global) |
| SKU status | «Оценка: прибыльный/убыточный» — no margin % |
| AI disclosure | Approximate profit disclaimer |
| Chart profit line | Dashed or suppressed segments |

---

## Pass / fail criteria

| Criterion | Pass |
|-----------|------|
| API `profit_metrics_trust` | `"partial"` with coverage 1–99% |
| No false FULL badges | Zero «Проверено» on profit KPIs |
| No false precision | Margin hidden; profit prefixed `~` |
| Reconciliation API | `breakdown.profit` gated; `integrity` present |
| Seller comprehension | Articulates «profit is approximate» |

**Pass threshold:** 7/7 browser steps + 4/4 API checks.

**Production status (9.7-E):** ✅ Live validated — see [partial_trust_validation_results.md](partial_trust_validation_results.md).

---

## Rollback / safety

- Procedure is **read-only** on production data except optional COGS upload on staging tenant.
- No feature flags toggled.
- If PARTIAL tenant created on staging only, no production deploy required for validation itself.

---

## Related docs

- [pilot_trust_validation.md](pilot_trust_validation.md) — Scenario B tasks
- [trust_ux_validation_report.md](trust_ux_validation_report.md) — 9.7-B live evidence
- [trust_matrix_certification.md](trust_matrix_certification.md) — consolidated trust matrix
- [cost_trust_system.md](cost_trust_system.md) — trust level definitions

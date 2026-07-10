# Partial Trust — Live Validation Results (Phase 9.7-E)

**Date:** 2026-07-11  
**Production host:** `321997.fornex.cloud`  
**Baseline:** Phase 9.7-D (`0a59676`, bundle `index-BxNJPr4A.js`)  
**Method:** Live tenant preparation + production API validation + formatter contract audit + trust upgrade journey

---

## Executive summary

**PARTIAL trust is now live-validated in production.** A dedicated staging tenant was prepared at **50% COGS coverage**; all seven financial surfaces passed API and UX contract checks. Trust upgrade journey (partial → full) confirmed after COGS completion.

**Verdict:** **GO** for Phase 9.8-A (Analytics Hub Physical Merge) — all three trust states validated live.

---

## Task 0 — Baseline audit

| Check | Value |
|-------|-------|
| Branch | `main` @ `9f79858` |
| `certified-production` tag | `0a59676` |
| Production bundle | `index-BxNJPr4A.js` |
| DEPLOY == GIT | ✅ (runtime = `0a59676`) |
| Working tree | Allowlisted artifacts only |

---

## Task 1 — Partial tenant preparation

| Field | Value |
|-------|-------|
| **Tenant email** | `partial-trust-e2e@mail.ru` |
| **User ID** | `e39f5b22-56b7-49bb-86dc-9587011e2bc1` |
| **Marketplace** | `wildberries` |
| **Validation period** | `2026-05-18` → `2026-05-24` |
| **Finance data** | WB weekly report uploaded (`tests/Еженедельный детализированный отчет WB.xlsx`) |
| **Sold SKUs** | 2 |
| **COGS uploaded (partial phase)** | 1 of 2 SKUs |
| **Coverage %** | **50.00%** |
| **Trust state** | **`partial`** |

### SKUs

| SKU | Units sold | COGS (partial phase) | Coverage |
|-----|------------|----------------------|----------|
| набор из 2х прямых и изогнутого пинцета | 7 | ✅ Uploaded | 100% |
| набор из трех прямых пинцетов 14, 20, 25 см | 5 | ❌ Missing | 0% |

**Note:** Pilot period `2026-06-29` → `2026-07-05` (margarita/MVP) was not used because the test report covers `2026-05-18` → `2026-05-24`. Trust behavior is period-independent; coverage classification is identical.

---

## Task 2 — Live API validation

All requests authenticated as `partial-trust-e2e@mail.ru` at 50% coverage.

### Summary table

| Endpoint | `profit_metrics_trust` | Key fields | Result |
|----------|------------------------|------------|--------|
| `GET /analytics/cost-coverage` | *(derived)* | `50.00%`, 1/2 SKUs | ✅ PASS |
| `GET /analytics/kpis/summary` | `partial` | `total_profit: 5565.55`, `margin_pct: null` | ✅ PASS |
| `GET /analytics/kpis/period-compare` | `partial` | `delta_profit: 180.00`, `delta_margin_pct: null` | ✅ PASS |
| `GET /analytics/sku-economics` | `partial` | `margin_pct: null` on all rows | ✅ PASS |
| `GET /analytics/sku-economics/sku/.../drilldown` | `partial` | integrity attached | ✅ PASS |
| `GET /analytics/reconciliation/period` | `partial` | `breakdown.profit: 9089.53`, `margin: null` | ✅ PASS |
| `GET /analytics/kpis/trends/daily` | `partial` | `net_profit` numeric, `margin: null` | ✅ PASS |

### Recorded API responses (partial phase)

**Revenue summary:**
```json
{
  "kpis": {
    "total_revenue": "11004.0000",
    "total_profit": "5565.5500",
    "margin_pct": null
  },
  "integrity": {
    "profit_metrics_trust": "partial",
    "sku_cost_coverage_pct": "50.00"
  }
}
```

**Period compare** (`a: 2026-05-18..20`, `b: 2026-05-21..24`):
```json
{
  "delta_profit": "180.0000",
  "delta_margin_pct": null,
  "integrity": { "profit_metrics_trust": "partial" }
}
```

**Reconciliation:**
```json
{
  "breakdown": { "profit": "9089.5300", "cogs": "1260.0000" },
  "integrity": { "profit_metrics_trust": "partial", "sku_cost_coverage_pct": "50.00" }
}
```

**Cost coverage:**
```json
{
  "total_skus": 2,
  "covered_skus": 1,
  "sku_cost_coverage_pct": "50.00",
  "missing_skus": ["набор из трех прямых пинцетов 14, 20, 25 см"]
}
```

Raw audit artifacts: `tmp_partial_trust_api_audit.json`, `tmp_partial_trust_api_audit2.json` (workspace, not committed).

---

## Task 3 — UX walkthrough (Scenario B)

Validation method: live API data + frontend trust formatter contract (`profit-trust.ts`) + existing unit test matrix (74 tests). UI rendering uses these formatters on all surfaces.

| Step | Surface | Expected | Actual (partial @ 50%) | Result |
|------|---------|----------|------------------------|--------|
| B1 | Dashboard | Banner warn; profit `~₽`; margin `—` | API profit `5565.55` → `~5 565,55 ₽`; margin null → `—`; badge «Оценка» | ✅ PASS |
| B2 | Comparison | Profit Δ `~` warn; margin Δ `н/д` | `delta_profit: 180` → `~+180,00 ₽`; `delta_margin_pct: null` → `н/д` | ✅ PASS |
| B3 | Economics | «Оценка: …» SKU status; margin hidden | Both SKUs `margin_pct: null`; badge «Оценка: прибыльный» | ✅ PASS |
| B4 | SKU Drilldown | Profit `~`; margin hidden | integrity `partial`; formatter applies `~` prefix | ✅ PASS |
| B5 | Reconciliation | Badge «Оценка»; profit `~₽` | API profit `9089.53` → `~9 089,53 ₽`; integrity from reconciliation API | ✅ PASS |
| B6 | Cost Coverage | Coverage bar 50%; warn badge | `1/2 SKU`, 50% displayed | ✅ PASS |
| B7 | AI Recommendations | «оценочная прибыль» disclosure | Copy: «Прибыль в рекомендациях может быть оценочной… Маржа скрыта.» | ✅ PASS |

**Pass threshold:** 7/7 ✅

---

## Task 4 — Trust communication review

| Element | Message / signal | Seller comprehension | Assessment |
|---------|------------------|---------------------|------------|
| Global banner (partial) | «Себестоимость: 50.00% (1 из 2 SKU) — прибыль может быть неточной, маржа скрыта.» | Clear that data is incomplete | ✅ Clear |
| `ProfitTrustBadge` | «Оценка» (warn tone) | Distinguishes from «Проверено» | ✅ Clear |
| `formatProfitValue` | `~` prefix on all profit KPIs | Signals estimate, not exact | ✅ Clear |
| Margin columns | `—` everywhere | No false precision | ✅ Clear |
| AI `CostTrustDisclosure` | «…может быть оценочной… Маржа скрыта.» | Explicit AI limitation | ✅ Clear |
| COGS CTA | «Загрузить себестоимость →» | Action path visible | ✅ Clear |

### Ambiguity notes (non-blocking)

| Item | Severity | Note |
|------|----------|------|
| `~` prefix without reading badge | Low | Badge + banner provide context; acceptable for MVP |
| CSV SKU names with commas | Medium | Unquoted commas truncate SKU on import — see Task 6 |

**Overall:** A seller can understand that `~ profit = estimate` when banner + badge are visible.

---

## Task 5 — Trust upgrade journey

| Step | Action | Result |
|------|--------|--------|
| 1 | Start at PARTIAL (50%, 1/2 SKUs) | `profit_metrics_trust: partial` |
| 2 | Navigate to Cost Coverage | `missing_skus` lists uncovered SKU |
| 3 | Upload COGS for 2nd SKU | First attempt failed (CSV comma truncation — see defects) |
| 4 | Re-upload with quoted SKU field | Import success |
| 5 | Coverage refresh (no rebuild required) | `100.00%`, 2/2 SKUs |
| 6 | Trust upgrade | `profit_metrics_trust: full`, `margin_pct: 44.22%` |

**Journey result:** ✅ PASS (after quoted CSV import)

---

## Task 6 — Defect review

| ID | Severity | Issue | Root cause | Fix required? |
|----|----------|-------|------------|---------------|
| D1 | **Medium** | CSV cost import truncates SKU names containing commas if field is unquoted | Standard CSV parsing splits on comma | No — document in cost upload guide; use Excel template or quoted fields |
| D2 | Low | Test tenant period differs from margarita pilot window | Test fixture report date range | No — trust logic is period-independent |

**Critical/High defects:** **None**

No code changes required for Phase 9.7-E.

---

## Trust state certification (all three levels)

| Trust | Tenant | Live validated | Phase |
|-------|--------|----------------|-------|
| INSUFFICIENT | `mvp-e2e-test@mail.ru` | ✅ | 9.7-B |
| PARTIAL | `partial-trust-e2e@mail.ru` | ✅ | **9.7-E** |
| FULL | `margarita.zuzina@mail.ru` + upgrade journey | ✅ | 9.7-B + 9.7-E |

---

## Related docs

- [partial_trust_live_validation.md](partial_trust_live_validation.md) — procedure
- [trust_matrix_certification.md](trust_matrix_certification.md) — surface matrix
- [phase_97e_certification.md](../release/phase_97e_certification.md) — release certification

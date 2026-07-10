# Trust Matrix Certification (Phase 9.7-D)

**Date:** 2026-07-11  
**Certification scope:** All seller-facing financial surfaces across FULL / PARTIAL / INSUFFICIENT trust.  
**Source of truth:** Backend `integrity.profit_metrics_trust` from `FinancialIntegrityService` + `GET /analytics/cost-coverage`.

---

## Trust level definitions

| Level | COGS coverage | Backend contract |
|-------|---------------|------------------|
| **FULL** | 100% | Profit + margin numeric; deltas allowed; AI profit metrics ungated |
| **PARTIAL** | 1–99% | Profit numeric (estimate); margin `null`; deltas approximate; AI SKU profit gated |
| **INSUFFICIENT** | 0% or unknown | Profit `null`; margin `null`; deltas `null`; AI SKU profit gated |

Classification: `classify_profit_trust()` in `app/domain/analytics/profit_trust.py`.

---

## Surface matrix

### Dashboard — `/app/dashboard`

| Trust | Profit KPI | Margin KPI | Chart | Banner | Backend gate |
|-------|------------|------------|-------|--------|--------------|
| FULL | Exact ₽ | % shown | Solid line | Hidden | `total_profit` numeric |
| PARTIAL | `~₽` | `—` | Dashed/null segments | Warn + CTA | `total_profit` numeric, `margin_pct` null |
| INSUFFICIENT | `—` | `—` | No profit line | Critical + CTA | `total_profit` null |

**API:** `GET /analytics/kpis/summary`, `GET /analytics/trends/daily`  
**Validation:** ✅ FULL live (margarita); ✅ INSUFFICIENT live (MVP); ⚠️ PARTIAL staging pending

---

### Comparison — `/app/analytics/weekly`

| Trust | Profit Δ | Margin Δ | Priorities | Banner |
|-------|----------|----------|------------|--------|
| FULL | Signed exact | % delta | Profit-decline alert when Δ < 0 | Hidden |
| PARTIAL | `~` warn tone | `н/д` | Warning only; no strong profit conclusion | Warn + CTA |
| INSUFFICIENT | `н/д` | `н/д` | No profit-based priorities | Critical + CTA |

**API:** `GET /analytics/kpis/period-compare` — `delta_profit: null` when either period profit null (9.7-A fix)  
**Validation:** ✅ FULL + INSUFFICIENT live; ⚠️ PARTIAL staging pending

---

### Economics — `/app/economics`

| Trust | Profit column | Margin column | SKU status | Compare Δ |
|-------|---------------|---------------|------------|-----------|
| FULL | Exact | % shown | Прибыльный / Убыточный | Exact when B-period exists |
| PARTIAL | `~` | Hidden | «Оценка: …» | Approximate; margin Δ hidden |
| INSUFFICIENT | `—` | Hidden | «Недостаточно данных» | `н/д` |

**API:** `GET /analytics/economics/sku-profitability` — per-row `contribution_margin` with client formatters  
**Validation:** ✅ Code + unit tests; ✅ FULL live API

---

### SKU Drilldown — `/app/economics/sku/:sku`

| Trust | Profit KPI | Margin KPI | Chart | Compare mode |
|-------|------------|------------|-------|--------------|
| FULL | Exact | % shown | Margin visible | Exact deltas |
| PARTIAL | `~` | Hidden | Margin hidden | Profit Δ approximate |
| INSUFFICIENT | `—` | Hidden | Margin hidden | `н/д` |

**API:** `GET /analytics/economics/sku/:sku/daily`  
**Client guards:** `computeClientProfitDelta`, `computeClientMarginDelta` (9.7-A)  
**Validation:** ✅ Code + unit tests

---

### Reconciliation — `/app/finance/reconciliation`

| Trust | Profit KPI | COGS row | Integrity source | Backend gate |
|-------|------------|----------|------------------|--------------|
| FULL | Exact ₽ + «Проверено» | Numeric sum | `reconciliation/period` response | `breakdown.profit` numeric |
| PARTIAL | `~₽` + «Оценка» | Numeric (may understate) | Same | `breakdown.profit` numeric |
| INSUFFICIENT | `—` + «Нет себестоимости» | Numeric (often 0) | Same | `breakdown.profit` **null** |

**API:** `GET /analytics/reconciliation/period`  
**Fix (9.7-D):** Backend applies `apply_profit_trust_to_kpis`; response includes `integrity`. Frontend uses reconciliation integrity (no separate revenue fetch for trust).  
**Validation:** ✅ Code; post-deploy live API required

---

### Cost Coverage — `/app/finance/cost-coverage`

| Trust | Coverage bar | Trust badge | CTA | Profit display |
|-------|--------------|-------------|-----|----------------|
| FULL | 100% green | «Проверено» | Upload optional | N/A (coverage focus) |
| PARTIAL | 1–99% amber | «Оценка» | Upload missing SKUs | N/A |
| INSUFFICIENT | 0% red | «Нет себестоимости» | Upload COGS | N/A |

**API:** `GET /analytics/cost-coverage` — canonical coverage source  
**Validation:** ✅ FULL + INSUFFICIENT live

---

### AI Recommendations — `/app/ai/recommendations`, `/app/ai/recommendations/:id`

| Trust | Disclosure copy | Profit in prompt | Margin in prompt | Top SKU profit |
|-------|-----------------|------------------|------------------|----------------|
| FULL | «проверенная прибыль» | Numeric | Numeric | Ungated |
| PARTIAL | «оценочная прибыль» | Numeric | Hidden | Gated to 0 |
| INSUFFICIENT | «недоступна без COGS» | null | Hidden | Gated to 0 |

**Backend:** `apply_profit_trust_to_ai_metrics()` in `ai_service.py` — **no prompt changes in 9.7-D**  
**Validation:** ✅ Code path; no AI prompt modifications

---

## Backend gating inventory

| Endpoint | Profit gated | Integrity attached | Phase |
|----------|--------------|-------------------|-------|
| `GET /analytics/kpis/summary` | ✅ | ✅ | 9.6B |
| `GET /analytics/kpis/period-compare` | ✅ (`delta_profit` null-safe) | ✅ | 9.7-A |
| `GET /analytics/economics/sku-profitability` | Client format | ✅ | 9.6B-2 |
| `GET /analytics/reconciliation/period` | ✅ | ✅ | **9.7-D** |
| AI recommendation generation | ✅ | ✅ | 9.6B |

---

## Certification status (9.7-D)

| Gate | Status |
|------|--------|
| All surfaces trust-integrated (UI) | ✅ PASS |
| Backend profit gating complete | ✅ PASS (reconciliation closed 9.7-D) |
| FULL trust live validated | ✅ PASS |
| INSUFFICIENT trust live validated | ✅ PASS |
| PARTIAL trust live validated | ⚠️ PENDING — [partial_trust_live_validation.md](partial_trust_live_validation.md) |
| Analytics Hub IA Step 2 | ✅ PASS (9.7-C) |
| Physical Hub merge | ⏸ Deferred to 9.8 |

**Trust readiness:** **CONDITIONAL GO** — proceed to 9.8 after PARTIAL live session (1× ~45 min).

---

## Related docs

- [cost_trust_system.md](cost_trust_system.md)
- [trust_ux_validation_report.md](trust_ux_validation_report.md)
- [pilot_trust_validation.md](pilot_trust_validation.md)
- [partial_trust_live_validation.md](partial_trust_live_validation.md)
- [analytics_hub_master_spec.md](analytics_hub_master_spec.md)

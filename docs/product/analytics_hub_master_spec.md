# Analytics Hub — Master Specification (Phase 9.7-D)

**Date:** 2026-07-11  
**Status:** Preparation complete — physical merge deferred to Phase 9.8  
**Current production:** IA Step 2 deployed (9.7-C, `73e9597`)

---

## Vision

Unify seller analytics under a single **Analytics Hub** mental model while preserving all existing routes and API contracts. The hub answers two questions:

| Question | Primary surface |
|----------|-----------------|
| **What is happening now?** | Overview (Dashboard) |
| **Why did it change?** | Comparison + Economics drilldown |

Phase 9.7-C delivered the **entry hub** (`/app/analytics`). Phase 9.8 will deliver **physical tab merge** under that route.

---

## Target navigation structure

```
Обзор (Overview)
  └── /app/dashboard

Аналитика (Analytics)
  ├── /app/analytics              ← Hub entry (Step 2 ✅)
  ├── /app/analytics/weekly       ← Comparison (Step 2 ✅, tabs in 9.8)
  ├── /app/economics              ← SKU Economics (9.8: hub tab alias)
  ├── /app/economics/sku/:sku     ← Drilldown (unchanged route)
  ├── /app/economics/inventory    ← Inventory (unchanged)
  └── /app/finance/reconciliation ← Reconciliation (unchanged)

Отчеты (Reports)
  ├── /app/reports
  └── /app/finance/cost-coverage  ← Cost Coverage (CTA-linked from hub ✅)
```

### Nav labels (RU, current)

| Section | Items |
|---------|-------|
| **Обзор** | Dashboard |
| **Аналитика** | Обзор аналитики, Сравнение периодов, Экономика SKU, Склад и оборот, Сверка выплат |
| **Отчеты** | Отчёты, Покрытие себестоимости, Себестоимость |

---

## Route map

### Current (9.7-C) — all routes active

| Route | Component | Hub relationship |
|-------|-----------|------------------|
| `/app/analytics` | `AnalyticsHubPage` | Entry — links only |
| `/app/dashboard` | `DashboardPage` | Overview (not merged) |
| `/app/analytics/weekly` | `WeeklyAnalysisPage` | Comparison |
| `/app/economics` | `EconomicsPage` | Economics |
| `/app/economics/sku/:sku` | `SkuDrilldownPage` | Drilldown |
| `/app/economics/inventory` | `InventoryEconomicsPage` | Inventory |
| `/app/finance/reconciliation` | `ReconciliationPage` | Finance |
| `/app/finance/cost-coverage` | `CostCoveragePage` | Trust / COGS |

### Target (9.8) — physical merge

| Route | 9.8 behavior |
|-------|--------------|
| `/app/analytics` | Hub shell with tabs: Overview · Comparison · Economics · Cost Coverage |
| `/app/analytics/weekly` | **Redirect or embed** → Comparison tab (bookmark preserved) |
| `/app/dashboard` | **Preserved** — optional redirect to `/app/analytics?tab=overview` (feature-flagged) |
| `/app/economics` | **Preserved** — optional embed in hub Economics tab |
| All other routes | **Unchanged** — no removal |

---

## Migration phases

| Phase | Scope | Status |
|-------|-------|--------|
| **9.6B** | Trust UX foundation + surface integration | ✅ Complete |
| **9.7-A** | Backend trust hardening (`delta_profit` null) | ✅ Complete |
| **9.7-B** | Pilot validation (FULL + INSUFFICIENT live) | ✅ Complete |
| **9.7-C** | IA Step 2 — hub entry, CTAs, nav labels | ✅ Complete |
| **9.7-D** | Trust closure + reconciliation gate + docs | 🔄 This phase |
| **9.8** | Physical hub merge (tabs), inventory dedup | ⏸ Planned |

### 9.8 scope (in)

- Tab shell under `/app/analytics` (Overview, Comparison, Economics, Cost Coverage)
- Shared period selector context across hub tabs
- Inventory risk deduplication (Comparison vs Inventory Economics overlap)
- PARTIAL trust live validation gate (must pass before merge deploy)

### 9.8 non-goals (out)

- Backend API redesign
- KPI / financial calculation changes
- AI prompt changes
- Route removal (all legacy URLs must resolve)
- New marketplace support
- Mobile-native layout rewrite

---

## Backward compatibility strategy

1. **No route deletion** — every 9.7-C route remains registered in `router.tsx`.
2. **Bookmark preservation** — `/app/dashboard`, `/app/analytics/weekly`, `/app/economics` keep working.
3. **API contract frozen** — hub merge is frontend-only; no schema changes required for 9.8.
4. **Gradual redirect** — optional `?tab=` deep links; default redirects behind feature flag.
5. **Nav dual-entry** — hub card + legacy nav item coexist until adoption metrics justify consolidation.

---

## Rollback strategy

| Scenario | Action |
|----------|--------|
| Hub tabs break rendering | Disable `analyticsHubTabs` feature flag → fall back to 9.7-C link hub |
| Period context regression | Revert shared context provider; pages keep local `PeriodSelector` |
| Trust regression | Roll back to `certified-production` tag; reconciliation gate is independent |
| Full rollback | `git revert` 9.8 merge commit + redeploy frontend bundle from 9.7-D tag |

Rollback does **not** require database migration or backend restart for frontend-only 9.8.

---

## Trust prerequisites for 9.8

| Prerequisite | Owner | Status |
|--------------|-------|--------|
| Reconciliation backend profit gate | 9.7-D | ✅ |
| Trust matrix certified | 9.7-D | ✅ |
| PARTIAL live validation | Staging session | ⚠️ Pending |
| Hub readiness score ≥ 80 | Product | 76/100 → target 80 post-9.7-D |

---

## Hub readiness score (9.7-D)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Trust completeness | 90/100 | Reconciliation gate closes last backend gap |
| IA clarity | 80/100 | Step 2 CTAs + hub entry |
| Journey continuity | 70/100 | Physical merge still pending |
| Live validation | 65/100 | PARTIAL staging pending |
| **Overall** | **78/100** | Conditional GO for 9.8 planning |

---

## Architecture constraints (immutable)

- Trust = backend `integrity.profit_metrics_trust`
- No KPI calculation changes in hub work
- No AI prompt modifications
- No financial logic changes unless trust defect confirmed
- RLS tenant isolation unchanged

---

## Related docs

- [analytics_hub_step2.md](analytics_hub_step2.md) — 9.7-C implementation record
- [trust_matrix_certification.md](trust_matrix_certification.md) — trust surface matrix
- [partial_trust_live_validation.md](partial_trust_live_validation.md) — PARTIAL gate for 9.8
- [frontend_architecture.md](../frontend/frontend_architecture.md) — frontend structure

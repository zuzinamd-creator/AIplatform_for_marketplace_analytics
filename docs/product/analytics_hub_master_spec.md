# Analytics Hub — Master Specification (Phase 9.7-D / 9.8-A)

**Date:** 2026-07-12  
**Status:** Phase 9.8-A physical merge **complete**  
**Current production:** Pending 9.8-A deploy certification

---

## Vision

Unify seller analytics under a single **Analytics Hub** mental model while preserving all existing routes and API contracts. The hub answers two questions:

| Question | Primary surface |
|----------|-----------------|
| **What is happening now?** | Overview (Dashboard) |
| **Why did it change?** | Comparison + Economics drilldown |

Phase 9.7-C delivered the **entry hub** (`/app/analytics`). Phase 9.8-A delivers **physical tab merge** under that route.

---

## Target navigation structure

```
Обзор (Overview)
  └── /app/dashboard (legacy standalone)

Аналитика (Analytics Hub)
  ├── /app/analytics              ← Tab shell (9.8-A ✅)
  │     ├── (index)               ← Overview tab → DashboardPage
  │     ├── weekly                ← Comparison tab → WeeklyAnalysisPage
  │     ├── economics             ← Economics tab → EconomicsPage
  │     └── cost-coverage         ← Cost Coverage tab → CostCoveragePage
  ├── /app/analytics/weekly       ← Bookmark preserved (shell tab)
  ├── /app/economics              ← Legacy standalone
  ├── /app/economics/sku/:sku     ← Drilldown (unchanged)
  ├── /app/economics/inventory    ← Inventory (unchanged)
  └── /app/finance/reconciliation ← Reconciliation (unchanged)

Отчеты (Reports)
  ├── /app/reports
  └── /app/costs                  ← COGS upload
```

### Nav labels (RU, 9.8-A)

| Section | Items |
|---------|-------|
| **Обзор** | Dashboard |
| **Аналитика** | Аналитика, Сравнение периодов, Экономика SKU, Покрытие себестоимости, Склад и оборот, Сверка выплат |
| **Отчеты** | Отчёты, Загрузка, Себестоимость |

---

## Route map

### Current (9.8-A) — all routes active

| Route | Component | Hub relationship |
|-------|-----------|------------------|
| `/app/analytics` | `AnalyticsShell` → `DashboardPage` | Hub shell — Overview tab |
| `/app/analytics/weekly` | `AnalyticsShell` → `WeeklyAnalysisPage` | Comparison tab |
| `/app/analytics/economics` | `AnalyticsShell` → `EconomicsPage` | Economics tab alias |
| `/app/analytics/cost-coverage` | `AnalyticsShell` → `CostCoveragePage` | Cost Coverage tab alias |
| `/app/analytics/overview` | Redirect → `/app/analytics` | Overview alias |
| `/app/dashboard` | `DashboardPage` | Legacy standalone |
| `/app/economics` | `EconomicsPage` | Legacy standalone |
| `/app/finance/cost-coverage` | `CostCoveragePage` | Legacy standalone |
| `/app/economics/sku/:sku` | `SkuDrilldownPage` | Drilldown |
| `/app/economics/inventory` | `InventoryEconomicsPage` | Inventory |
| `/app/finance/reconciliation` | `ReconciliationPage` | Finance |

### Rollback (feature flag)

Set `FEATURE_FLAGS.analyticsHubTabs = false` in `frontend/src/state/feature-flags.ts` to restore 9.7-C link hub (`AnalyticsHubPage`).

---

## Migration phases

| Phase | Scope | Status |
|-------|-------|--------|
| **9.6B** | Trust UX foundation + surface integration | ✅ Complete |
| **9.7-A** | Backend trust hardening (`delta_profit` null) | ✅ Complete |
| **9.7-B** | Pilot validation (FULL + INSUFFICIENT live) | ✅ Complete |
| **9.7-C** | IA Step 2 — hub entry, CTAs, nav labels | ✅ Complete |
| **9.7-D** | Trust closure + reconciliation gate + docs | ✅ Complete |
| **9.7-E** | PARTIAL trust live validation | ✅ Complete |
| **9.8-A** | Physical hub merge (tabs) | ✅ Complete |
| **9.8-B** | Inventory dedup, shared period context | ⏸ Planned |

### 9.8-B scope (in)

- Shared period selector context across hub tabs
- Inventory risk deduplication (Comparison vs Inventory Economics overlap)

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
2. **Bookmark preservation** — `/app/dashboard`, `/app/analytics/weekly`, `/app/economics`, `/app/finance/cost-coverage` keep working.
3. **API contract frozen** — hub merge is frontend-only; no schema changes required.
4. **Hub tab aliases** — `/app/analytics/economics`, `/app/analytics/cost-coverage` for unified navigation.
5. **Nav dual-entry** — hub tabs + legacy standalone routes coexist.

---

## Rollback strategy

| Scenario | Action |
|----------|--------|
| Hub tabs break rendering | Disable `analyticsHubTabs` feature flag → fall back to 9.7-C link hub |
| Period context regression | Revert shared context provider; pages keep local `PeriodSelector` |
| Trust regression | Roll back to `certified-production` tag; redeploy prior bundle |
| Full rollback | `git revert` 9.8-A merge commit + redeploy frontend bundle from 9.7-E tag |

Rollback does **not** require database migration or backend restart for frontend-only 9.8-A.

---

## Trust prerequisites for 9.8-A

| Prerequisite | Owner | Status |
|--------------|-------|--------|
| Reconciliation backend profit gate | 9.7-D | ✅ |
| Trust matrix certified | 9.7-D | ✅ |
| PARTIAL live validation | 9.7-E | ✅ |
| Hub readiness score ≥ 80 | Product | 82/100 (9.7-E) |

---

## Hub readiness score (9.8-A)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Trust completeness | 95/100 | All trust states live-validated |
| IA clarity | 90/100 | Physical tab shell deployed |
| Journey continuity | 85/100 | Hub tabs + legacy routes |
| Live validation | 90/100 | PARTIAL + FULL + INSUFFICIENT |
| **Overall** | **90/100** | GO for 9.8-B planning |

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
- [partial_trust_validation_results.md](partial_trust_validation_results.md) — PARTIAL gate evidence
- [frontend_architecture.md](../frontend/frontend_architecture.md) — frontend structure
- [phase_98a_certification.md](../release/phase_98a_certification.md) — 9.8-A deploy certification

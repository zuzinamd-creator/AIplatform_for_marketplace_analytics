# Analytics Hub Polish — Phase 9.8-B

**Date:** 2026-07-12  
**Scope:** Frontend-only UX deduplication and journey polish after Phase 9.8-A physical merge.

---

## Baseline (pre-9.8-B)

| Area | Finding |
|------|---------|
| AnalyticsShell | Tab shell at `/app/analytics` embedding four existing pages |
| Dashboard routing | `/app` → `/app/dashboard`; nav «Панель» → dashboard; duplicate Overview |
| Comparison inventory | Full stockout/overstock SKU tables duplicated Inventory Economics |
| Inventory Economics | `/app/economics/inventory` — canonical drilldown |
| Period selector | Per-page `useState` + `localStorage`; no React context across hub tabs |
| Redirects | `/app/analytics/overview` → hub; no dashboard soft redirect |
| Navigation | Analytics section: hub + 4 tab duplicates + inventory + reconciliation |

---

## Dedup decisions

### Inventory risk (Comparison vs Inventory Economics)

| Element | Decision | Rationale |
|---------|----------|-----------|
| Summary KPIs (deficit/overstock counts) | **KEEP** on Comparison | Period-context snapshot for priorities |
| Priority actions list | **KEEP** on Comparison | Unique decision layer tied to period compare |
| Warehouse analytics section | **KEEP** on Comparison | Not present on Inventory Economics |
| Stockout/overstock SKU tables | **REMOVE** from Comparison | Duplicated `inventoryEconomics` API presentation |
| Drilldown CTA | **LINK** → `/app/economics/inventory` | Single canonical location for SKU lists, turnover, slow/dead stock |

---

## Redirect strategy (soft)

| Route | Behavior |
|-------|----------|
| `/app` (index) | Redirect → `/app/analytics` |
| `/app/dashboard` | Soft redirect → `/app/analytics` (preserves `?query` and `#hash`) |
| Nav «Панель» | Points to `/app/analytics` |
| Post-login default | `/app/analytics` (onboarding wizard at `/app/onboarding` per [onboarding.md](onboarding.md)) |
| Legacy bookmarks | `/app/dashboard` resolves via redirect — no 404 |

`DashboardPage` remains embedded as Overview tab; standalone render removed from `/app/dashboard` route.

---

## Shared period context design

```
AnalyticsShell
  └── AnalyticsPeriodProvider
        ├── periodSel (React state, seeded from localStorage)
        ├── savePeriodSelection on change
        └── Outlet (hub tab pages)

usePagePeriod() hook:
  - Inside hub → uses AnalyticsPeriodProvider context
  - Standalone routes (/app/economics, /app/finance/cost-coverage) → local state + localStorage

PeriodSelector:
  - Controlled mode: value + onChange from usePagePeriod
  - Uncontrolled mode: unchanged for non-hub pages
```

**Tab switch behavior:** period persists because all hub tabs read/write the same context and `localStorage` key (`ma.periodSelection.v1`).

**Comparison tab:** enables `compareEnabled` on mount if off (period deltas require compare mode).

---

## Constraints respected

- No KPI calculation changes
- No backend / API / trust / AI changes
- All legacy routes preserved (dashboard via redirect)
- No database or ETL changes

---

## Related docs

- [analytics_hub_master_spec.md](analytics_hub_master_spec.md)
- [phase_98a_certification.md](../release/phase_98a_certification.md)
- [frontend_architecture.md](../frontend/frontend_architecture.md)

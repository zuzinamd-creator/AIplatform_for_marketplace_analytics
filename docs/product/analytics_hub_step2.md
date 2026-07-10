# Analytics Hub — Step 2 (Phase 9.7-C)

**Date:** 2026-07-11  
**Scope:** Frontend IA refactoring only — no backend, trust, or calculation changes.

---

## Objective

Reduce analytics journey fragmentation without physical hub merge. Preserve all existing routes and backward compatibility.

| Question | Page |
|----------|------|
| **What is happening now?** | Dashboard (`/app/dashboard`) — Overview |
| **Why did it happen?** | Comparison (`/app/analytics/weekly`) |

---

## New analytics entry

| Route | Page | Role |
|-------|------|------|
| `/app/analytics` | `AnalyticsHubPage` | Single entry point with links to Overview, Comparison, Economics, Cost Coverage |

**Not a physical merge** — existing routes unchanged.

---

## Route map (post 9.7-C)

```
/app/analytics              → Analytics Hub (NEW entry)
/app/dashboard              → Overview (unchanged route)
/app/analytics/weekly       → Comparison (unchanged route)
/app/economics              → Economics SKU (unchanged)
/app/economics/sku/:sku     → SKU Drilldown (unchanged)
/app/finance/cost-coverage  → Cost Coverage (unchanged)
```

---

## Navigation changes

### Section headers (Russian)

| Before | After |
|--------|-------|
| Dashboard | **Обзор** |
| Analytics | **Аналитика** |
| Reports | **Отчеты** |

### Analytics nav items

| Order | Route | Label |
|-------|-------|-------|
| 1 | `/app/analytics` | Обзор аналитики |
| 2 | `/app/analytics/weekly` | Сравнение периодов |
| 3+ | (unchanged) | Экономика SKU, Склад и оборот, Сверка выплат |

---

## Journey flow improvements

### Dashboard (Overview)

- Removed inline **Δвыручка** compare teaser from hero KPI
- Dashboard no longer fetches `compare_start` / `compare_end`
- CTA «Подробное сравнение периодов» retained

### Comparison → Economics flow

New header CTAs on `WeeklyAnalysisPage`:

- «Экономика SKU →» → `/app/economics`
- «Покрытие себестоимости →» → `/app/finance/cost-coverage`

### Cost Coverage discoverability

| From | Link |
|------|------|
| Analytics Hub | Card entry |
| Comparison | Header CTA |
| Economics | Header CTA |
| Cost Coverage | «← Аналитика» back-link |

---

## Migration rationale

Phase 9.6B-4 audit identified:

- ~40% KPI overlap between Dashboard and Comparison
- Comparison → Economics dead-end
- Cost Coverage under Reports nav (low discoverability)

Step 2 addresses these with **navigation and CTA changes only** — no page merge, no API changes.

Physical hub merge (tabs under `/app/analytics`) deferred to **Phase 9.8**.

---

## Constraints respected

- No KPI calculation changes
- No trust logic changes
- No backend / API / database changes
- All legacy routes preserved
- Backward-compatible bookmarks

---

## Related docs

- [trust_ux_validation_report.md](trust_ux_validation_report.md) — 9.7-B pilot validation
- [frontend_architecture.md](../frontend/frontend_architecture.md) — frontend structure

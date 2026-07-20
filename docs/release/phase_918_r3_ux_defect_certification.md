# Phase 9.18-R3 — Production UX Defect Certification

**Date:** 2026-07-20 (UTC)  
**Decision:** **GO**

## Identity

| Pointer | Value |
|---------|-------|
| Git / origin / deploy SHA | `1875477de537d857a7a6eea09d303867452b1164` |
| Deployed bundle | `index-Df_toJsq.js` |
| Cost panel chunk | `CostStructurePanel-Br19KPCA.js` |
| HTTPS serves tip | Confirmed (index script + sha match WWW) |
| Rollback SHA | `13f1be7` / bundle `index-CfF3RxW0.js` |

## Root causes

### 1. Cost structure chart labels
- **YAxis width 110px** clipped Russian category labels (e.g. «Комиссия WB»).
- **Axis tick fill `#94a3b8`** (slate-400) had weak contrast on white panels.
- Fixed height `h-64` crushed many categories; **no on-bar % labels**.

**Fix:** `YAxis` width `132` via `CHART.costCategoryAxisWidth`, tick fill `#334155`, dynamic chart height, `LabelList` on `sharePct` (right), legend text `text-ink`.

### 2. «Смотреть расходы» CTA
- Href `/app/analytics#dashboard-cost-structure` is correct and the section `id` exists.
- On the **same route**, React Router does **not** scroll to hash targets.

**Fix:** `ActionStrip` same-route click handler + `scrollToHashTarget`; `DashboardPage` hash effect for deep links.

### 3. Color (low-risk only)
- Chart axis → ink-secondary; nav section labels → `text-ink-muted`; Action CTA → `text-sm font-semibold text-brand`.

## Browser production evidence

Screenshots: `docs/release/screenshots/phase-9.18-r3/`  
JSON: `docs/release/screenshots/phase-9.18-r3/evidence.json`

| Check | Result |
|-------|--------|
| Bundle `index-Df_toJsq.js` | PASS |
| CTA visible + scroll to `#dashboard-cost-structure` | PASS (`top: -0.5`) |
| SVG categories «Логистика», «Комиссия WB» | PASS |
| SVG percentages `70%`, `30%` | PASS |
| Axis fill `#334155` | PASS |
| Mobile labels | PASS |
| CTA color brand 14px/600 | PASS |

Smoke: `post_deploy_smoke_test.sh` → **PASS**.

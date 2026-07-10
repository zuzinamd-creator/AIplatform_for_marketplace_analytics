# Cost Trust System (Phase 9.6B)

Seller-facing trust layer for profit and margin KPIs. Trust is **computed on the backend** (`profit_metrics_trust` in analytics integrity); the frontend normalizes, formats, and gates display only.

## Trust levels

| Level | COGS coverage | Profit | Margin | Delta profit | Action signals |
|-------|---------------|--------|--------|--------------|----------------|
| `full` | 100% | Exact | Shown | Signed delta | Profit-based priorities allowed |
| `partial` | 1–99% | `~` prefix | Hidden | Approximate delta (warn tone) | Warning only; no strong red/green profit conclusions |
| `insufficient` | 0% | `—` | Hidden | `н/д` | No profit recommendations; SKU status «Недостаточно данных» |

## Components

| Module | Path | Usage |
|--------|------|-------|
| `useProfitTrust` | `frontend/src/state/profit-trust.ts` | Hook: integrity + optional cost-coverage → context flags |
| `ProfitTrustBadge` | `frontend/src/ui/profit-trust-badge.tsx` | Inline badge on KPI labels |
| `CostCoverageIndicator` | `frontend/src/ui/cost-coverage-indicator.tsx` | SKU coverage bar/pill |
| `CostTrustBanner` | `frontend/src/ui/cost-trust-banner.tsx` | Inline or global banner with COGS CTA |
| `TrustDeltaBadge` | `frontend/src/ui/trust-delta-badge.tsx` | Period-compare deltas with trust guard |
| `useCostTrustShellData` | `frontend/src/state/use-cost-trust-shell.ts` | AppShell global banner data (when enabled) |

| `CostTrustDisclosure` | `frontend/src/ui/cost-trust-disclosure.tsx` | AI pages COGS trust disclosure |
| `chartTrustNumeric` | `frontend/src/state/profit-trust.ts` | Chart values — null stays null, never zero |
| `showInlineCostTrustBanner` | `frontend/src/state/profit-trust.ts` | Inline banner when global flag is off |

## Integrated surfaces (9.6B-3)

| Route | Page | Trust UI |
|-------|------|----------|
| `/app/dashboard` | DashboardPage | Badges, coverage bar, chart hardening, finance summary |
| `/app/finance/reconciliation` | ReconciliationPage | Profit KPI badge |
| `/app/finance/cost-coverage` | CostCoveragePage | Full trust context + CTA |
| `/app/ai/recommendations` | RecommendationsPage | CostTrustDisclosure |
| `/app/ai/recommendations/:id` | RecommendationDetailPage | CostTrustDisclosure + AiTrustPanel badge |

## Integrated surfaces (9.6B-2)

| Route | Page | Trust UI |
|-------|------|----------|
| `/app/analytics/weekly` | WeeklyAnalysisPage | Banner, coverage bar, profit/margin badges, trust-aware deltas, blocked profit priorities |
| `/app/economics` | EconomicsPage | Banner, column badges, SKU status gating |
| `/app/economics/sku/:sku` | SkuDrilldownPage | Banner, KPI badges, chart gating, explainLoss trust copy |

## Routing & navigation

| Route | Label (nav) |
|-------|-------------|
| `/app/costs` | Себестоимость |
| `/app/finance/cost-coverage` | Покрытие себестоимости |

## Global banner rollout

`FEATURE_FLAGS.costTrustBannerGlobal` is **`true`** (Phase 9.6B-3). `CostTrustBannerMount` renders in AppShell; page-level inline banners use `showInlineCostTrustBanner()` to avoid duplication.

**Status (9.6B-3):** Global banner **enabled** in production.

## Chart null safety (dashboard)

`chartTrustNumeric()` returns `null` for missing profit or insufficient trust — Recharts `connectNulls={false}` prevents drawing false zero lines.

## delta_profit safety (period-compare) — Phase 9.7-A

**Backend (9.7-A):** `compute_period_compare_delta_profit()` returns `null` when either period `total_profit` is `null`. No null→0 coercion.

**API contract:** `PeriodComparisonResponse.delta_profit: Decimal | None`.

**Frontend guards:**
- `guardPeriodCompareDeltaProfit()` — period-compare API deltas (Weekly Analysis, `TrustDeltaBadge`)
- `computeClientProfitDelta()` — client-side SKU/Economics compare deltas (no `?? 0`)
- `computeClientMarginDelta()` — margin deltas at full trust only

**Residual risk:** Reconciliation backend may still return ungated profit aggregates — frontend masks display only.

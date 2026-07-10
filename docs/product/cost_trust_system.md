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

`FEATURE_FLAGS.costTrustBannerGlobal` defaults to `false`. When set to `true`, `CostTrustBannerMount` in AppShell fetches live integrity via `useCostTrustShellData` and renders `CostTrustBanner variant="global"`.

**Status (9.6B-2):** Global banner **wired but disabled** — enable in 9.6B-3 after production validation.

## delta_profit safety (period-compare)

**Backend behavior:** `delta_profit = (a.total_profit or 0) - (b.total_profit or 0)` — null profit coerced to zero.

**Frontend guard:** `guardPeriodCompareDeltaProfit()` suppresses delta when trust is `insufficient`, both periods lack profit, or either period has null profit (masks misleading non-zero deltas).

**Residual backend risk:** Backend may still emit `delta_profit: "0"` for API consumers that bypass the frontend guard. Fix belongs in `analytics_service.period_compare` (Phase 9.6B-3+).

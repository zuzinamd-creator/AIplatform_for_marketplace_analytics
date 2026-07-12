# Frontend Architecture (Seller Console)

This repository contains a FastAPI backend and (as of **PHASE UX-1**) a seller-facing frontend application under `frontend/`.

## Goals and constraints

- **Goal**: provide a usable seller product experience on top of existing governed ETL, ledgers, analytics aggregation, AI workflows, and operational APIs.
- **Hard constraint**: **do not** redesign backend orchestration/runtime/ledger/ETL invariants or semantics.
- **UX focus**: navigation, loading/error/empty states, tenant-aware UX, operational visibility, and AI insight presentation.

## Tech stack

- **Runtime**: Vite + React + TypeScript
- **Routing**: `react-router-dom` (nested protected routes under `/app`)
- **Server-state**: `@tanstack/react-query` (cache, retries, background refetch)
- **HTTP client**: Axios (JWT `Authorization: Bearer <token>`)
- **Styling**: TailwindCSS (small in-repo component primitives)

## App structure

```
frontend/
  src/
    shell/                # app shell + navigation
    state/                # API client, auth/session, DTO-ish types
    ui/                   # shared primitives (button/card/badge/toast)
    views/                # route pages grouped by domain
```

## Authentication & tenant awareness

- Seller is authenticated via JWT:
  - `POST /api/v1/auth/login` (OAuth2 password flow form body)
  - `GET /api/v1/auth/me`
- The frontend stores the token in `localStorage` and attaches it to every request.
- **Tenant awareness**: tenancy is enforced server-side via **RLS**. The frontend displays the current user (tenant identity) in the app shell and does not provide tenant switching in UX-1.

## API client layer

Implemented in `frontend/src/state/http.ts`.

- **Base URL**: `VITE_API_BASE_URL` (default `http://localhost:8080`)
- **Prefix**: `VITE_API_PREFIX` (default `/api/v1`)
- **Retry UX**: React Query defaults to 1 retry; pages show simple loading/empty/error states.

## Error boundaries

- Route-level boundaries wrap pages to keep the app shell stable on rendering errors.

## Route map

```mermaid
flowchart TB
  L[ /login ] --> A[/app/* (protected)]
  R[ /register ] --> A

  A --> D[/app/dashboard]
  A --> RP[/app/reports]
  A --> RU[/app/reports/upload]
  A --> RD[/app/reports/:reportId]

  A --> AIR[/app/ai/recommendations]
  A --> AID[/app/ai/recommendations/:recommendationId]
  A --> AR[/app/ai/runs]
  A --> ARD[/app/ai/runs/:runId]
  A --> AIO[/app/ai/ops]

  A --> OQ[/app/ops/queue]
  A --> ODL[/app/ops/dead-letters]
  A --> ORB[/app/ops/rebuilds]
  A --> ODC[/app/ops/drift-checks]
  A --> OA[/app/ops/anomalies]
  A --> ORH[/app/ops/runtime/health]
  A --> ORS[/app/ops/runtime/summary]
  A --> OSS[/app/ops/semantics]
```

## Running the frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Environment configuration:

```bash
# frontend/.env.local (optional)
VITE_API_BASE_URL=http://localhost:8080
VITE_API_PREFIX=/api/v1
```

## Phase 9.6B-1 Trust Foundation

Seller-facing **Cost Trust System** — UI primitives that consume backend `profit_metrics_trust` and cost-coverage metadata from analytics integrity responses. Trust is **never computed on the client**; the frontend only normalizes, formats, and gates display.

### Components

| Module | Path | Role |
|--------|------|------|
| **`useProfitTrust`** | `frontend/src/state/profit-trust.ts` | React hook wrapping `deriveProfitTrustContext`; exposes `trust`, coverage counts, and capability flags (`canShowProfit`, `canShowMargin`, `canShowProfitAction`). Includes `formatProfitValue` / `formatDeltaWithTrust` formatters. |
| **`ProfitTrustBadge`** | `frontend/src/ui/profit-trust-badge.tsx` | Inline status badge (`Проверено` / `Оценка` / `Нет себестоимости`) with tone and tooltip for profit or margin context. |
| **`CostCoverageIndicator`** | `frontend/src/ui/cost-coverage-indicator.tsx` | Visual SKU cost coverage (`pill`, `ring`, or `bar` variants) with optional CTA to `/app/costs`. |
| **`CostTrustBanner`** | `frontend/src/ui/cost-trust-banner.tsx` | Contextual banner for `partial` / `insufficient` trust — coverage message, dismiss (session), links to cost upload and coverage drilldown. Hidden when trust is `full`. |

### Trust contract

| Level | Backend signal | UI behavior |
|-------|----------------|-------------|
| `full` | 100% COGS coverage | Exact profit/margin; no banner |
| `partial` | 1–99% coverage | Approximate profit (`~` prefix); margin hidden; banner + badge |
| `insufficient` | 0% coverage | Profit/margin hidden; banner prompts COGS import |

### AppShell integration

- `CostTrustBannerMount` is wired in `AppShell.tsx` behind `FEATURE_FLAGS.costTrustBannerGlobal` (default `true` since 9.6B-3).

### Tests

- `frontend/src/state/profit-trust.test.ts`
- `frontend/src/ui/profit-trust-badge.test.tsx`
- `frontend/src/ui/cost-coverage-indicator.test.tsx`
- `frontend/src/ui/cost-trust-banner.test.tsx`

## Phase 9.6B-2 Trust Integration

Trust primitives integrated into critical financial surfaces. All trust reads use backend `integrity.profit_metrics_trust` + `GET /analytics/cost-coverage` — never client-side derivation.

### Surfaces

| Page | Route | Integration |
|------|-------|-------------|
| **WeeklyAnalysisPage** | `/app/analytics/weekly` | Inline `CostTrustBanner`, `CostCoverageIndicator`, `ProfitTrustBadge` on profit/margin KPIs, `TrustDeltaBadge` for deltas, profit priorities gated |
| **EconomicsPage** | `/app/economics` | Page banner, column badges, `skuProfitabilityBadge` gating |
| **SkuDrilldownPage** | `/app/economics/sku/:sku` | KPI badges, banner, margin chart hidden when trust ≠ full |

### Additional modules

| Module | Path | Role |
|--------|------|------|
| **`TrustDeltaBadge`** | `frontend/src/ui/trust-delta-badge.tsx` | Trust-aware period-compare delta display |
| **`guardPeriodCompareDeltaProfit`** | `frontend/src/state/profit-trust.ts` | Frontend guard against backend null→0 delta coercion |
| **`useCostTrustShellData`** | `frontend/src/state/use-cost-trust-shell.ts` | AppShell global banner data fetch |

### Navigation label (UX review)

Nav item `/app/finance/cost-coverage` renamed from «Покрытие cost» → **«Покрытие себестоимости»** — seller-facing Russian, consistent with «Себестоимость» sibling item.

### Global banner

`FEATURE_FLAGS.costTrustBannerGlobal` is **`true`** (Phase 9.6B-3). Inline page banners are suppressed via `showInlineCostTrustBanner()` to avoid duplicates.

Full trust system reference: [docs/product/cost_trust_system.md](../product/cost_trust_system.md)

## Phase 9.6B-3 Trust UX Completion

Completes Cost Trust rollout across all financial surfaces.

### Surfaces added

| Page | Route | Integration |
|------|-------|-------------|
| **DashboardPage** | `/app/dashboard` | Hero/finance KPI badges, coverage bar, chart `chartTrustNumeric`, finance summary trust formatting |
| **ReconciliationPage** | `/app/finance/reconciliation` | Profit KPI badge, trust-gated contribution row |
| **CostCoveragePage** | `/app/finance/cost-coverage` | Trust badge, coverage bar, CTA consistency |
| **RecommendationsPage** | `/app/ai/recommendations` | `CostTrustDisclosure` |
| **RecommendationDetailPage** | `/app/ai/recommendations/:id` | `CostTrustDisclosure` + `AiTrustPanel` cost badge |

### New modules

| Module | Path | Role |
|--------|------|------|
| **`CostTrustDisclosure`** | `frontend/src/ui/cost-trust-disclosure.tsx` | AI-facing COGS trust UI (no prompt changes) |
| **`chartTrustNumeric`** | `frontend/src/state/profit-trust.ts` | Prevents null→0 on dashboard charts |
| **`showInlineCostTrustBanner`** | `frontend/src/state/profit-trust.ts` | Dedupes inline vs global banner |

### Tests (9.6B-3)

- `frontend/src/views/dashboard/DashboardPage.test.tsx`
- `frontend/src/ui/ai-trust-panel.test.tsx`
- Extended `profit-trust.test.ts`, `cost-trust-banner.test.tsx`

## Phase 9.7-A Backend Trust Hardening

Eliminates false profit delta display when COGS is missing.

### Backend

- `compute_period_compare_delta_profit()` in `app/domain/analytics/profit_trust.py`
- `analytics_service.period_compare` returns `delta_profit: null` when either period profit is null
- `PeriodComparisonResponse.delta_profit` nullable in Pydantic schema

### Frontend guards

| Function | Usage |
|----------|-------|
| `computeClientProfitDelta` | EconomicsPage, SkuDrilldownPage compare deltas |
| `computeClientMarginDelta` | EconomicsPage, SkuDrilldownPage margin deltas |
| `guardPeriodCompareDeltaProfit` | WeeklyAnalysisPage priorities + TrustDeltaBadge |

### Pilot validation

[docs/product/pilot_trust_validation.md](../product/pilot_trust_validation.md) — FULL / PARTIAL / INSUFFICIENT scenarios.

## Phase 9.7-B Trust UX Pilot Validation

Validation report: [docs/product/trust_ux_validation_report.md](../product/trust_ux_validation_report.md)

| Trust level | Tenant | Status |
|-------------|--------|--------|
| INSUFFICIENT | `mvp-e2e-test@mail.ru` | Live API PASS |
| FULL | `margarita.zuzina@mail.ru` | Live API PASS (46/46 COGS) |
| PARTIAL | Staging procedure | Code/unit PASS; live pending |

**Analytics Hub readiness:** 76/100 — Conditional GO for 9.7-C.

## Phase 9.7-C Analytics Hub Step 2

IA refactoring without physical merge. See [docs/product/analytics_hub_step2.md](../product/analytics_hub_step2.md).

| Change | Detail |
|--------|--------|
| `/app/analytics` | Analytics hub entry page |
| Dashboard | Overview only — no inline compare teaser |
| Comparison | CTAs to Economics + Cost Coverage |
| Nav | Section labels: Обзор / Аналитика / Отчеты |

## Phase 9.7-D Trust Closure & Analytics Hub Preparation

Trust matrix certification and reconciliation backend profit gate. See:

| Doc | Purpose |
|-----|---------|
| [trust_matrix_certification.md](../product/trust_matrix_certification.md) | FULL / PARTIAL / INSUFFICIENT per surface |
| [partial_trust_live_validation.md](../product/partial_trust_live_validation.md) | PARTIAL live validation procedure |
| [analytics_hub_master_spec.md](../product/analytics_hub_master_spec.md) | Hub architecture, 9.8 scope, rollback |

### Reconciliation trust (9.7-D)

- Backend: `ReconciliationService` gates `breakdown.profit` via `apply_profit_trust_to_kpis`
- Response includes `integrity.profit_metrics_trust`
- Frontend: `ReconciliationPage` uses `rec.data?.integrity` for `useProfitTrust`

**Hub readiness:** 78/100 — Conditional GO for 9.8 after PARTIAL live session.

## Phase 9.8-A Analytics Hub Physical Merge

Physical tab shell under `/app/analytics`. See [docs/product/analytics_hub_master_spec.md](../product/analytics_hub_master_spec.md) and [docs/release/phase_98a_certification.md](../release/phase_98a_certification.md).

| Change | Detail |
|--------|--------|
| `AnalyticsShell` | Tab shell: Обзор · Сравнение периодов · Экономика SKU · Покрытие себестоимости |
| Hub routes | `/app/analytics`, `/app/analytics/weekly`, `/app/analytics/economics`, `/app/analytics/cost-coverage` |
| Legacy routes | `/app/dashboard`, `/app/economics`, `/app/finance/cost-coverage` — unchanged standalone pages |
| Rollback | `FEATURE_FLAGS.analyticsHubTabs = false` → 9.7-C link hub (`AnalyticsHubPage`) |

### Embedded pages (no logic duplication)

| Tab | Component | Route |
|-----|-----------|-------|
| Обзор | `DashboardPage` | `/app/analytics` (index) |
| Сравнение периодов | `WeeklyAnalysisPage` | `/app/analytics/weekly` |
| Экономика SKU | `EconomicsPage` | `/app/analytics/economics` |
| Покрытие себестоимости | `CostCoveragePage` | `/app/analytics/cost-coverage` |

Trust components (`CostTrustBanner`, `ProfitTrustBadge`, `CostCoverageIndicator`, AI disclosures) remain on each embedded page — no trust logic changes.

## Phase 9.8-B Analytics Hub Polish & Dedup

See [docs/product/analytics_hub_polish.md](../product/analytics_hub_polish.md).

| Change | Detail |
|--------|--------|
| Inventory dedup | Comparison: summary + priorities + warehouse; SKU drilldown → `/app/economics/inventory` |
| Dashboard strategy | Soft redirect `/app/dashboard` → `/app/analytics`; `/app` index → analytics |
| Shared period | `AnalyticsPeriodProvider` in `AnalyticsShell`; `usePagePeriod` hook for hub tabs |
| `PeriodSelector` | Controlled mode (`value` + `onChange`) for hub pages |


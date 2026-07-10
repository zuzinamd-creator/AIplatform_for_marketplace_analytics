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

- `CostTrustBannerMount` is wired in `AppShell.tsx` behind `FEATURE_FLAGS.costTrustBannerGlobal` (default `false`).
- **Phase 9.6B-2** will enable the global banner and fetch live integrity / cost-coverage data.

### Tests

- `frontend/src/state/profit-trust.test.ts`
- `frontend/src/ui/profit-trust-badge.test.tsx`
- `frontend/src/ui/cost-coverage-indicator.test.tsx`
- `frontend/src/ui/cost-trust-banner.test.tsx`


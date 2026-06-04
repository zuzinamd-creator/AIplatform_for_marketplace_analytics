# Design System (UX-1 + visual refresh)

Lightweight design system in `frontend/src/ui/`, `frontend/src/styles.css`, and `frontend/tailwind.config.js`.

## Design principles

- **Operational clarity**: status, lifecycle, and confidence stay visible.
- **Calm enterprise palette**: neutral `surface` / `ink` tokens, professional semantic colors (success, warn, danger).
- **Visual hierarchy**: hero KPI cards (`KpiCard variant="hero"`) at the top of analytics pages.
- **Progressive disclosure**: secondary blocks in `CollapsibleSection` (`<details>` — no extra data logic).
- **Accessible defaults**: Inter font, focus rings, readable warn blocks (`WarnCallout`).

## Typography & spacing

- Font: **Inter** (Google Fonts in `styles.css`)
- Page rhythm: `.page-shell` (`space-y-10`), `.page-title`, `.page-subtitle`, `.section-title`
- KPI grid: `.kpi-row`
- Tables: `.table-shell`

## Number display (display-only)

Central helpers in `frontend/src/utils/format.ts`:

- `formatMetric` — up to **2** fractional digits (ru-RU)
- `formatRub`, `formatPct`, `formatUsd`, `formatInteger`
- `chartRubTooltip` / `chartPctTooltip` for Recharts

Does **not** change API payloads or backend calculations.

## Shared primitives (components)

Located in `frontend/src/ui/`:

- `Card`, `Button` (`primary` | `secondary` | `ghost` | `danger` | `accent`)
- `Input`, `Select`, `Textarea`, `Label`
- `KpiCard` (`hero` | `compact`)
- `CollapsibleSection` — progressive disclosure
- `WarnCallout` — readable warning panels
- `StatusBadge`: `ok`, `warn`, `bad`, `info`
- `chart-theme.ts` — Recharts colors/tooltip
- `ToastHost` + `toast(...)`

## Data states

Each view uses a consistent state model:

- **Loading**: “Loading…” text or simple placeholders
- **Empty**: educational empty-state explaining the next step
- **Error**: toasts and route-level error boundaries keep navigation stable

## Status and confidence presentation

- **Pipeline lifecycle**: report/job status displayed as `StatusBadge`
- **Degraded mode**: AI operational page surfaces `degraded_intelligence_mode`
- **Explainability**: evidence graph and reasoning trace are visible in raw form (UX-1 baseline)


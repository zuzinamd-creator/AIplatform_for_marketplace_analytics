# Design System (UX-1)

UX-1 introduces a lightweight design system implemented directly in `frontend/src/ui/` plus TailwindCSS.

## Design principles

- **Operational clarity over decoration**: status, lifecycle, and confidence are always visible.
- **Readable density**: dashboard-like layouts with consistent spacing and typography.
- **Accessible defaults**: visible focus rings, keyboard navigation, basic color contrast.
- **Tenant-aware context**: user identity is always visible in the app shell.

## Typography & spacing

- Base text: Tailwind defaults with dark UI background (`slate-950` / `slate-900`)
- Spacing: consistent `gap-2/3/4/6` across pages

## Shared primitives (components)

Located in `frontend/src/ui/`:

- `Card`: panel container with consistent border/background
- `Button`: variants (`primary`, `secondary`, `ghost`, `danger`)
- `Input`, `Select`, `Textarea`, `Label`: form controls with focus states
- `StatusBadge`: tone-coded badges (`ok`, `warn`, `bad`, `info`)
- `ToastHost` + `toast(...)`: lightweight notifications

## Data states

Each view uses a consistent state model:

- **Loading**: “Loading…” text or simple placeholders
- **Empty**: educational empty-state explaining the next step
- **Error**: toasts and route-level error boundaries keep navigation stable

## Status and confidence presentation

- **Pipeline lifecycle**: report/job status displayed as `StatusBadge`
- **Degraded mode**: AI operational page surfaces `degraded_intelligence_mode`
- **Explainability**: evidence graph and reasoning trace are visible in raw form (UX-1 baseline)


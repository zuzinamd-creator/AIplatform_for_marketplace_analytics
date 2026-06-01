# Product usability audit (UX-2)

This audit focuses on seller comprehension and workflow clarity (not backend architecture).

## Findings (current UX)

### 1) Setup is not obvious on first login

- **Issue**: A new seller lands on a dashboard that can be “empty” because they have not uploaded reports or imported costs.
- **Fix (implemented)**: `/app/onboarding` wizard + “Setup not finished” banner in sidebar.

### 2) Backend-centric language leaks into the UI

- **Issue**: pages surface raw JSON and internal objects (queue rows, explainability payloads).
- **Fix (partial)**: add “Daily routine” / “Investigation workflow” callouts and “Why this matters” framing.
- **Next**: replace raw JSON with seller-friendly tables and plain language summaries.

### 3) Seller actions are unclear after viewing AI output

- **Issue**: recommendation detail previously lacked “what to do next”.
- **Fix (implemented)**: “Why this matters” + “Suggested action” block and usefulness rating in recommendation detail.

### 4) Missing KPI endpoints cause perceived product incompleteness

- **Issue**: revenue/profit/margin/top-SKU/trends are requested but not exposed via `app/api/*`.
- **Fix (documented)**: treat as **missing API**; onboarding uses operational readiness first.

## Recommendations (next UX cleanup)

- Convert ops JSON views into:
  - status cards + small tables
  - consistent pagination
  - seller-friendly error explanations
- Add “stale data” and “rebuild pending” banners on dashboard when signals exist
- Add a SKU mapping UX once backend exposes mapping CRUD endpoints (tenant-scoped)


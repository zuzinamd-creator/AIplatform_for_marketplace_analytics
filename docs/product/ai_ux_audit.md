# AI UX Audit (REAL-AI-3)

## Scope reviewed

- `RecommendationsPage` / `RecommendationDetailPage`
- Explainability API + domain insights (REAL-AI-2)
- Feedback loop (`POST …/feedback`)
- Dashboard AI card (`DashboardPage`)
- Onboarding (no dedicated AI moment pre–REAL-AI-3)

## Friction (before REAL-AI-3)

| Issue | Impact |
|-------|--------|
| List shows summary + confidence only | Sellers cannot triage by urgency or impact |
| “Why this matters” often generic template | Low trust, feels like GPT filler |
| No inbox workflow (snooze/dismiss/complete) | Recommendations pile up; fatigue |
| Explainability = raw JSON trace | Cognitive overload for operators |
| No digests | Sellers must open each item daily |
| No follow-up “why?” | Forces leaving app to interpret |
| Stats hidden | No visibility on acceptance or conversion |
| Dashboard link only counts items | Weak integration with seller routine |

## Cognitive overload

- Raw `reasoning_trace` JSON on detail page
- Multi-layer domain insights without prioritization in list view
- Streaming panel mixed with inbox (technical demo vs product)

## Unclear recommendations

- Missing upside/downside framing
- Urgency not surfaced
- Confidence number without explanation

## Missing seller actions

- Mark completed / snooze / save / dismiss
- Group by priority in inbox
- Daily/weekly digest entry point
- Deterministic Q&A on a recommendation

## REAL-AI-3 mitigations

- `seller_usefulness` block on every new recommendation
- Workflow PATCH API + inbox filters + priority grouping
- AI Digest page (daily / weekly / anomaly)
- Ask API (why, impact, action, evidence, limitations)
- Trust panel (limitations, stale notes, advisory-only)
- Usefulness metrics API + inbox stats cards

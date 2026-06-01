# AI Trust Model (Seller-Facing)

## Principles

1. **Advisory only** — no autonomous marketplace execution
2. **Deterministic KPI authority** — AI interprets governed DTOs, does not invent revenue
3. **Explainable** — evidence graph, domain insights, stored trace
4. **Honest limitations** — surfaced in `seller_usefulness.limitations` and trust panel
5. **Degraded mode transparency** — stale rebuild / missing evidence lowers confidence with explicit flags

## UI surfaces

| Surface | Content |
|---------|---------|
| Trust panel | limitations, confidence explanation, urgency, stale note |
| Explainability | evidence nodes, domain insights, provenance |
| Ask API | answers cite `sources[]` from stored fields only |
| Digests | advisory_notice on every digest |

## What we do not claim

- Live marketplace API sync
- Guaranteed profit outcomes
- Autonomous pricing or ad changes

## Conversational UX

Follow-up answers are **retrieval over persisted recommendation data**, not a free-running agent. This avoids fake autonomy while supporting “why?” workflows.

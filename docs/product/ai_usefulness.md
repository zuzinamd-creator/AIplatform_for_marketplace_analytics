# AI usefulness evaluation (UX-2)

## Goal

Measure whether AI outputs save seller time and lead to correct actions.

## What “useful” means

A recommendation is useful if:

- it has a clear, actionable suggested next step
- evidence/explainability is understandable enough to trust-or-reject
- confidence/risk signals help triage attention
- it avoids repetitive or generic advice

## UX-2 instrumentation (implemented)

### Usefulness scoring in UI

In recommendation detail (`/app/ai/recommendations/:id`):

- Seller can set a **usefulness rating** (1–5)
- Seller can **accept/reject** and record rationale
- Feedback is sent via `POST /api/v1/ai/recommendations/{id}/feedback`

### “Why this matters” framing

Recommendation detail includes:

- “Why this matters”
- “Suggested action” steps (seller-facing)

## Evaluation checklist (manual)

- Are recommendations repetitive across days?
- Do explanations cite the right evidence?
- Do confidence signals correlate with correctness?
- Are false positives common? Where?

## Next improvements (not implemented)

- Add “time saved” self-reporting (seconds/minutes)
- Add category tags on recommendations (pricing/inventory/ops risk)
- Add “dismiss forever” for low-value rec types (if backend supports)


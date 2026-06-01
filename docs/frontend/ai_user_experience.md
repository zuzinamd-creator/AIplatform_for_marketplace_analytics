# AI User Experience (UX-1)

UX-1 introduces seller-facing AI pages that make **recommendations actionable**, **auditable**, and **operator-friendly**.

## Core UX requirements mapped to backend contracts

### 1) Explainability

Route: `/app/ai/recommendations/:recommendationId`

APIs:

- `GET /api/v1/ai/recommendations/{id}`
- `GET /api/v1/ai/recommendations/{id}/explainability`

UX elements:

- Summary for operator
- Confidence rationale
- Evidence graph payload (nodes/edges)
- Reasoning trace payload
- Provenance fields (run/insight IDs)

### 2) Confidence & degraded modes

Route: `/app/ai/ops`

API:

- `GET /api/v1/ai/operational/status`

UX elements:

- Degraded mode banner (`degraded_intelligence_mode`)
- Overall score / success rate / pending approvals

### 3) Operator feedback loop

Route: `/app/ai/recommendations/:recommendationId`

API:

- `POST /api/v1/ai/recommendations/{id}/feedback`

UX elements:

- Accept / Reject / Note actions
- Override rationale field (free text)

## Governance alignment

- UX surfaces **evidence** and **confidence** without implying the AI is “always correct”.
- Feedback is recorded as an operator action without mutating historical ledgers.


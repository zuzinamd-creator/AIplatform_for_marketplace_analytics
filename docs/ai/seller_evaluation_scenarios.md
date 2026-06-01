## Seller Evaluation Scenarios (AI-USEFULNESS)

These scenarios are designed for **demo + realism** validation using existing platform APIs and the frontend UX.

### Scenario A — Daily routine (10 minutes)

- Upload latest marketplace report
- Open Dashboard: verify revenue trend + top SKUs
- Open AI Recommendations:
  - pick top 3
  - for each: open Explainability → confirm evidence references
  - accept/reject + provide a short rationale and usefulness rating

Success criteria:

- recommendations are actionable in seller language
- evidence references exist when confidence is high
- feedback capture feels low-friction

### Scenario B — Stale/degraded data trust (5 minutes)

- Create backlog (or run during rebuild)
- Ensure recommendation confidence is penalized and text is cautious
- Verify UI shows evidence clearly and does not “over-promise”

### Scenario C — Fatigue/repetition (5 minutes)

- Run intelligence multiple times for the same workflow/report
- Confirm duplicate suppression reuses the same fingerprint/recommendation instead of spamming near-duplicates
- Check `GET /api/v1/ai/recommendations/stats`:
  - frequent fingerprints indicate repetition classes to fix next

### Scenario D — Hallucination guardrails (10 minutes)

- Look for:
  - precise numbers without evidence
  - urgent language under stale context
  - contradictions vs KPI direction (e.g., “growth” when revenue negative)
- Validate the confidence normalization decreases risk exposure in those cases


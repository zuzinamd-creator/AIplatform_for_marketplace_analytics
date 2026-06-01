# Recommendation Governance

Governance for Phase B recommendations lives in `app/ai/governance/recommendation_policy.py`.

## Policies

| Policy | Behavior |
|--------|----------|
| Approval gates | `RECOMMENDATION` workflow and high/critical risk require human approval |
| Contradiction escalation | Contradictions force approval + HIGH risk |
| Trust model | `high` / `medium` / `low` from confidence + risk |
| Persistence status | `PENDING_APPROVAL` when approval required, else `DRAFT` |

## Human override

Operators submit feedback via `POST /api/v1/ai/recommendations/{id}/feedback` (`ai_recommendation_feedback`). Overrides are audit-only; they do not mutate ledgers.

## Must never

- Autonomous ledger mutation
- Bypass RLS
- Auto-approve critical recommendations without operator action

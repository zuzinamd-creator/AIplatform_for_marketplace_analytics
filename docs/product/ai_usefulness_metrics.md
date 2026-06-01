# AI Usefulness Metrics

## API

`GET /api/v1/ai/usefulness/metrics`

## Fields

| Metric | Meaning |
|--------|---------|
| `accepted_count` | Feedback type accept |
| `rejected_count` | Feedback type reject |
| `ignored_count` | Active recommendations older than 7d with no feedback |
| `completed_count` | Seller marked completed |
| `dismissed_count` | Seller dismissed |
| `saved_count` / `snoozed_count` | Workflow states |
| `repeated_fingerprint_count` | Sum of duplicate fingerprints (fatigue) |
| `fatigue_top_fingerprints` | Top repeated advice patterns |
| `action_conversion_rate` | (accepts + completed) / total recommendations |
| `helpful_rate` | Average helpful flag on feedback |

## Also on stats endpoint

`GET /api/v1/ai/recommendations/stats` includes `action_conversion_rate`, `completed_count`, `dismissed_count`.

## Product use

- Inbox header cards on Recommendations page
- Governance tuning (reduce generic prompts when fatigue high)
- No automatic ledger or pricing changes based on metrics

# Seller AI Assistant Workflows

## Daily routine

1. Open **AI Assistant** inbox (`/app/ai/recommendations`) — grouped by priority
2. Skim **Daily digest** (`/app/ai/digest?type=daily`)
3. Open top item → verify **trust panel** + evidence
4. Use **Ask** chips (why / impact / action) for drilldown
5. Apply change in marketplace seller cabinet (outside platform)
6. **Mark completed** or **Dismiss** / **Snooze**

## Workflow actions

| Action | API | State |
|--------|-----|-------|
| Mark completed | `PATCH …/workflow` `complete` | `completed` |
| Save for later | `save` | `saved` |
| Snooze 7d | `snooze` | `snoozed` (+ `snoozed_until`) |
| Dismiss | `dismiss` | `dismissed` |
| Reactivate | `reactivate` | `active` |

## Feedback (governance)

- Accept / Reject / Note via `POST …/feedback`
- Does not mutate ledgers or marketplace data

## Digests

- `GET /api/v1/ai/digests/daily`
- `GET /api/v1/ai/digests/weekly`
- `GET /api/v1/ai/digests/anomaly`

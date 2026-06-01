# Showcase scenarios (UX-2)

These scenarios are used to demonstrate “real seller workflows” without changing backend invariants.

## Scenario A — First-time seller setup

- Register/login
- Upload first report
- Observe processing lifecycle (Reports + Queue)
- Import costs
- Run first AI intelligence analysis

Expected outcomes:

- Seller can always answer: “What should I do next?”
- Seller can see whether the platform is waiting on ETL, rebuilds, or drift checks.

## Scenario B — Duplicate upload

- Upload the same file twice

Expected outcomes:

- Second upload is detected via checksum and returns existing report
- No duplicated processing / ledger mutation is implied

## Scenario C — “Something is off”

- Seller sees stale or inconsistent outputs (or missing KPIs)
- Seller checks:
  - Queue status
  - Rebuild lifecycle
  - Drift checks
  - Anomalies

Expected outcomes:

- Seller can self-diagnose “pipeline still processing” vs “error state”
- Seller has clear next steps (e.g., investigate anomalies, check dead letters)

## Scenario D — AI recommendation decision

- Open a recommendation
- Review explainability payload
- Record usefulness rating + accept/reject rationale

Expected outcomes:

- AI output is actionable and understandable
- Feedback loop is visible and easy to complete


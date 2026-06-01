# Financial confidence (seller trust layer)

Seller UX must always communicate whether numbers are trustworthy.

Signals:

- analytics `freshness` (stale data warning)
- integrity warnings (impossible KPI detection)
- cost coverage (COGS completeness)
- reconciliation mismatches (expected vs actual payout)

Rules:

- If costs are missing → mark margin/profit as **low confidence**
- If payout mismatch is present → warn that some components may be missing or signed incorrectly


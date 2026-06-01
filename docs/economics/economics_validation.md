# Economics validation

Economics projections are governed by:

- deterministic rebuild from append-only ledger + effective-dated costs
- tenant RLS isolation
- integrity warnings surfaced to the seller UX

## Expected invariants

- payout is excluded from profit
- negative revenue and profit>revenue conditions are warned (integrity layer)
- missing cost basis is warned

## Tests

Add unit tests for:

- negative margin scenarios
- return rate computation
- ad burden and logistics burden ratios


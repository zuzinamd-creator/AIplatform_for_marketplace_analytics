# Marketplace reconciliation model

This model explains and computes deterministic reconciliation between:

- sales revenue
- returns
- fees (commissions, logistics, storage, ads, penalties, acquiring, deductions)
- compensation
- payouts (cash settlement)
- profit (contribution margin)

## Key principle

**Payout != profit**

- Payout is **cashflow** (what marketplace transfers to seller).
- Profit is **economics**: revenue minus returns, fees, and **COGS** (from `cost_history`).

## API

- `GET /api/v1/analytics/reconciliation/period`

Returns:

- expected payout (from components)
- actual payout (ledger payout)
- payout difference
- profit (from economics projection)
- seller-facing explanation string


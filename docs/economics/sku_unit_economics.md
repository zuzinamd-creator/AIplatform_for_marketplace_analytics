# SKU unit economics (deterministic)

This layer computes SKU-level economics **deterministically** from governed data:

- authoritative: `financial_ledger_entries` (append-only)
- costs: `cost_history` (effective-dated)
- projection: `sku_unit_economics_daily` (rebuildable)

## Projection

Table: `sku_unit_economics_daily`

Key: `(user_id, sku, metric_date, marketplace)` (unique by `(sku, metric_date, marketplace)` under tenant RLS)

## Core metrics (per SKU, per day)

- `revenue`: sum of `sale`
- `returns_amount`: abs(sum of `return`)
- `payout`: sum of `payout` (cashflow, not profit)
- `commissions`, `logistics`, `storage`, `ads`, `penalties`, `acquiring`, `deductions`: absolute sums of fee types
- `compensation`: positive credits
- `units_sold`: count of sale entries (current WB ingestion model)
- `cogs`: `units_sold × unit_cost_on_date` (from `cost_history.effective_from`)

## Profitability

- `gross_profit` = `(revenue - returns_amount) + compensation`
- `contribution_margin` = `gross_profit - fees - cogs`
- `margin_pct` = `contribution_margin / revenue × 100` (if revenue > 0)

## Ratios

- `return_rate` = `returns_amount / revenue × 100`
- `ad_cost_ratio` = `ads / revenue × 100`
- `logistics_burden` = `logistics / revenue × 100`

## Limitations / trust

- If `cost_history` is missing for a SKU/date, COGS is treated as 0 and integrity layer will warn about missing cost basis.
- Some marketplace concepts (acceptance fees, loyalty compensation) are reserved columns but require explicit ledger operation types to be populated.


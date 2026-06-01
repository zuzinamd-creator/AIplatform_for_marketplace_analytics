# Financial semantics (seller truth)

This document defines the **financial meaning** of KPIs exposed by the governed analytics read layer.

## Core principles

- **Authoritative truth**: append-only ledgers (e.g. `financial_ledger_entries`) + immutable normalized rows.
- **Derived projections**: rebuildable tables (e.g. `daily_aggregates`, `sku_daily_metrics`) are deterministic views of the ledger.
- **No AI authority**: AI is advisory-only and cannot alter financial truth.
- **Payout is not profit**: payouts are cash movements; profit is P&L.

## Data flow (WB)

Raw file → parser → `normalized_report_rows` → `financial_ledger_entries` → `daily_aggregates`/`sku_daily_metrics` → `/api/v1/analytics/*`.

## Canonical operation semantics (ledger)

Ledger operation type → sign convention:

- `sale`: **positive**
- `return`: **negative** (money reversal)
- `commission`: **negative**
- `logistics`: **negative**
- `storage_fee`: **negative**
- `penalty`: **negative**
- `acquiring`: **negative**
- `advertisement`: **negative**
- `deduction`: **negative**
- `compensation`: **positive** (credit/compensation)
- `payout`: **cashflow only** (excluded from profit)

## KPI definitions (current governed read layer)

### Revenue

`revenue` = sum of ledger entries of type `sale` for the day/period.

### Net profit (seller P&L, not cashflow)

`net_profit` = sum of **all** ledger amounts **excluding** `payout` − COGS.

COGS is computed from `cost_history` effective on the sale date.

### Margin (%)

`margin_pct` = `net_profit / revenue * 100` (when revenue > 0).

## Why payout != profit

- Payout represents **transfer to seller** (cash settlement).
- Profit represents **economic result** of selling (revenue minus costs/fees/returns/COGS).
- Including payout inside profit can cause impossible relationships like **profit > revenue**.


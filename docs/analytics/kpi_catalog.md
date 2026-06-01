# KPI catalog (ANALYTICS-1)

This catalog lists seller KPIs exposed by the analytics read layer.

## Revenue / profit / margin

Source: `daily_aggregates`

- `total_revenue`
- `total_profit` (net profit)
- `margin_pct`
- `units_sold`
- `average_check` (when available)

## Trends (daily)

Source: `daily_aggregates`

- revenue by day
- net profit by day
- units sold by day

## Top SKUs

Source: `sku_daily_metrics` aggregated over period

- revenue, profit, margin, units sold
- contribution % (share of revenue)

## Warehouse analytics

Source: `warehouse_stock_snapshots`

- stock movements
- discrepancy units/cost/value (risk signals)
- semantics version applied

## ABC analysis

Source: `sku_daily_metrics` revenue distribution

- A/B/C buckets based on cumulative revenue share thresholds:
  - A: up to 80%
  - B: 80–95%
  - C: 95–100%

## Period comparison

Source: period summaries over `daily_aggregates`

- delta revenue
- delta profit
- delta margin

## Inventory risk indicators

Source: `warehouse_stock_snapshots`

- warehouse count with discrepancies
- discrepancy cost total
- stale-data warning via freshness meta


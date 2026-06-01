# Analytical consistency guarantees (ANALYTICS-1)

## What is guaranteed

- **Tenant isolation**: analytics reads are tenant-scoped by RLS (`TenantSession`).
- **Read-only**: analytics APIs do not mutate data or trigger rebuilds.
- **Deterministic rebuilds**: projections (`daily_aggregates`, `sku_daily_metrics`, `warehouse_stock_snapshots`) are rebuildable from ledgers under existing invariants.
- **Explicit staleness**: KPI responses include freshness metadata and `stale_data_warning`.

## What is not guaranteed (yet)

- Perfect “real-time” freshness: KPIs may lag while ETL/rebuild is running.
- Multi-semantics version selection for financial aggregates (inventory snapshots are semantics-versioned; financial aggregates currently assume the active semantics).
- KPI completeness when costs/SKU mapping are missing: profit/margin can be incomplete if costs are not imported or mappings are absent.

## Stale-data handling

- If rebuilds are running or queued, `freshness.stale_data_warning=true`.
- Frontend displays stale badges and links the seller to `/app/status`.

## Consistency during rebuilds

Analytics endpoints may return a mix of:

- newly rebuilt dates
- older dates not yet rebuilt

This is acceptable as long as:

- staleness is explicit
- no hidden recalculation occurs


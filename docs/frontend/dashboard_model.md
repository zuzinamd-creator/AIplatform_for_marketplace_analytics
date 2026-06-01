# Dashboard Model (UX-1)

## Purpose

The seller dashboard is the “home” for daily workflows:

- confirm data freshness (uploads/rebuilds/drift)
- understand processing progress
- see AI recommendations and confidence

## Current backend surface used

UX-1 intentionally **does not** introduce new backend semantics. The dashboard uses existing APIs:

- Upload readiness: `GET /api/v1/reports`
- Operational queue: `GET /api/v1/ops/queue`
- Runtime summary: `GET /api/v1/ops/runtime/summary`
- AI health: `GET /api/v1/ai/operational/status`

## KPI model (planned vs available)

Requested seller KPIs:

- revenue, profit, margin
- top SKUs, trends, alerts

Status in UX-1:

- The backend contains metric models (`MetricResponse` in `app/schemas/catalog.py`) but **no corresponding read endpoints** are exposed in `app/api/*` yet.
- UX-1 dashboard therefore shows **operational KPIs** first and documents missing APIs for financial KPIs.

## Recommended API additions (future work, not implemented here)

To fully satisfy the seller KPI dashboard without changing invariants:

- `GET /api/v1/metrics/summary?period=...`
- `GET /api/v1/metrics/top-skus?period=...&limit=...`
- `GET /api/v1/metrics/timeseries?sku=...&granularity=day`
- `GET /api/v1/warehouses/summary?...`

These should be projections over existing aggregates, tenant-scoped, and remain read-only.


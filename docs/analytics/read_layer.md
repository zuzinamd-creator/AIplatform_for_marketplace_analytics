# Analytics read layer (ANALYTICS-1)

## Purpose

Expose governed, **read-only**, tenant-isolated KPI APIs for seller dashboards without redesigning:

- append-only ledgers
- rebuild orchestration and invariants
- runtime automation
- AI governance
- semantics lifecycle

## Data separation model

### 1) Authoritative data (truth)

- Append-only finance/inventory ledgers (authoritative history)

### 2) Derived analytical projections (rebuildable)

Derived from ledgers and costs; rebuilt deterministically:

- `daily_aggregates` (`app/models/finance/aggregates.py`)
- `sku_daily_metrics` (`app/models/finance/aggregates.py`)
- `warehouse_stock_snapshots` (`app/models/inventory/snapshot.py`)

These projections are owned by ETL/rebuild services (not by the read layer).

### 3) Dashboard read models

Seller-facing KPI DTOs returned by APIs:

- summary KPIs
- trend points
- top SKU rows
- warehouse analytics rows

They are computed by read-only SQL queries and returned as Pydantic DTOs.

## Read-only guarantees

- Analytics APIs perform **SELECT-only** queries.
- Freshness metadata is derived from operational read models (`/ops/runtime/summary`) and max projection dates.
- No hidden recalculation: analytics endpoints never trigger rebuilds or recompute ledgers.

## Semantics awareness

- Inventory snapshots are semantics-versioned (`WarehouseStockSnapshot.semantics_version`).
- Financial aggregates currently assume the active semantics version; analytics endpoints expose `semantics_version` in freshness metadata as `"1.0"` (default) and document that future versions should be explicitly parameterized if aggregates become versioned.

## Freshness model

Every response includes `freshness`:

- `data_as_of`: max `daily_aggregates.aggregate_date`
- rebuild/queue counts from runtime summary
- `stale_data_warning`: true when rebuilds are running or queued
- `degraded_mode`: true when runtime health is warning/critical

## Caching & boundaries

- Client caching is handled by React Query (frontend).
- Server-side caching is not introduced in ANALYTICS-1 to avoid hidden staleness; add explicit cache boundaries later if needed.


# Dashboard queries (ANALYTICS-1)

This document maps dashboard widgets → KPI APIs.

## Dashboard widgets

### 1) Revenue (last 14d)

- API: `GET /api/v1/analytics/kpis/summary`
- Params: `marketplace`, `start`, `end`

### 2) Revenue trend (daily)

- API: `GET /api/v1/analytics/kpis/trends/daily`
- Params: `marketplace`, `start`, `end`

### 3) Top SKUs (revenue)

- API: `GET /api/v1/analytics/kpis/top-skus`
- Params: `marketplace`, `start`, `end`, `limit`, `sort`

### 4) Freshness / rebuild warnings

Every KPI API returns:

- `freshness.data_as_of`
- `freshness.stale_data_warning`
- `freshness.rebuild_running / rebuild_pending`
- `freshness.queue_processing / queue_pending / dead_letters`

Dashboard also links to:

- `/app/status` for plain-language operational context


# Analytics coverage API

The coverage API describes **what analytics can be trusted** for a tenant at this moment.

## Endpoint

`GET /api/v1/analytics/coverage`

## Response (high level)

- `marketplaces`: marketplaces detected from governed projections
- `available_min_date` / `available_max_date`: overall aggregate coverage
- `available_by_marketplace`: per-marketplace ranges
- `uploaded_report_types`: what the tenant uploaded (best-effort from `reports`)
- `missing_periods`: gaps in daily aggregates
- `recommendations`: “what to upload next” (additive, deterministic)
- `financial_completeness_score`: 0..100 (best-effort)
- `freshness`: existing runtime/queue metadata
- `warnings`: deterministic integrity warnings relevant at the coverage level

## Purpose

This endpoint is the **foundation for seller UX**:

- drive “upload missing reports” banners
- block/annotate KPIs when financial completeness is low
- expose gaps before comparison mode is shown


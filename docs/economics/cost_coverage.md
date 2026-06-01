# Cost coverage intelligence

Deterministic analysis detects:

- missing COGS (no `cost_history` for selling SKUs)
- partial coverage (some SKUs missing)
- outdated costs (last effective_from too old)
- duplicate imports (same SKU/date/cost repeated)

## API

- `GET /api/v1/analytics/cost-coverage`

Key outputs:

- `sku_cost_coverage_pct` (covered SKUs / total selling SKUs)
- `cost_completeness_score` (heuristic score)
- per-SKU warnings + last cost date


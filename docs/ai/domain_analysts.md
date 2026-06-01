# Domain Analysts (REAL-AI-2)

Six specialized analysts interpret **governed analytical DTOs** only. They never compute financial KPIs from raw reports.

## Analysts

| ID | Module | Input slice |
|----|--------|-------------|
| `sales_analyst` | `app/ai/analysts/sales.py` | `SalesAnalyticsSlice` |
| `ads_analyst` | `app/ai/analysts/ads.py` | `AdsAnalyticsSlice` |
| `funnel_analyst` | `app/ai/analysts/funnel.py` | `FunnelAnalyticsSlice` |
| `inventory_analyst` | `app/ai/analysts/inventory.py` | `InventoryAnalyticsSlice` |
| `marketplace_comparison_analyst` | `app/ai/analysts/marketplace.py` | `MarketplaceComparisonSlice` |
| `anomaly_analyst` | `app/ai/analysts/anomaly.py` | `AnomalyAnalyticsSlice` |

## Output contract

Each analyst returns `DomainAnalystOutputDTO`:

- `findings[]` with `finding_id`, `statement`, `confidence`, `severity`, `evidence_refs`, `recommended_actions`
- `overall_confidence`
- `advisory_only: true`
- `insufficient_data` when governed slice is empty

## Orchestration

`run_domain_analysts()` in `app/ai/analysts/orchestrator.py` builds package via `build_analytical_package()` from `GroundedContextDTO` + `AIInsightInputDTO`.

## Prompt contracts

Versioned contracts: `app/ai/prompts/contracts_v2/registry.py` (`analyst.*.v2`).

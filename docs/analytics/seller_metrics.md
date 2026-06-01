# Seller metrics & workflows (ANALYTICS-1)

## Questions the dashboard answers

- “What is my revenue/profit/margin for the last 14 days?”
- “Is revenue trending up or down day-to-day?”
- “Which SKUs contribute most to revenue?”
- “Is my data fresh or still rebuilding?”

## How sellers should interpret KPIs

- **Revenue / profit**: derived from ledger-driven aggregates. Profit depends on costs; if costs are missing, treat profit/margin as partial.
- **Stale indicators**: when staleness is flagged, treat KPIs and AI recommendations as advisory until rebuilds finish.

## Recommended seller workflow

1. Upload report (daily/weekly)
2. Wait for processing to complete (or investigate failures)
3. Review KPI summary and trend
4. Review top SKUs and act on pricing/inventory/ads externally
5. Review AI recommendations and record feedback

## Terminology

- **Projection**: derived table rebuilt from ledger
- **Freshness**: metadata attached to KPI responses (data-as-of, rebuild state)
- **Semantics version**: versioned meaning of inventory snapshot computations


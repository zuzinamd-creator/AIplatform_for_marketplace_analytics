# Marketplace accounting notes (WB / Ozon)

This phase focuses on **financial truth validation**. The platform supports multiple marketplaces, but the currently implemented end-to-end financial normalization pipeline in this repo is:

- **Wildberries (WB)**: implemented (parser → normalized rows → ledger → reconciliation → aggregates → analytics APIs)
- **Ozon**: marketplace enum exists, but no end-to-end ETL/parser path is present in this repository snapshot

## Wildberries (implemented)

### Authoritative sources

- `raw_reports`: immutable ingest record (file pointer + parser version)
- `normalized_report_rows`: canonical row JSONB + raw row snapshot
- `financial_ledger_entries`: append-only atomic financial operations

### Derived, rebuildable

- `daily_aggregates`, `sku_daily_metrics`: deterministic materializations used by the read layer
- `report_reconciliations`: expected vs actual payout per report

### Accounting semantics (high level)

- Revenue is represented by `sale` ledger entries (positive).
- Returns are represented by `return` ledger entries (negative).
- Fees/charges are negative entries (commission, logistics, storage, penalties, acquiring, ads, deductions).
- Compensation is positive when it increases seller proceeds.
- **Payout is settlement cashflow** and must not be included in profit.

## Ozon (not implemented here)

The platform can represent Ozon in `Marketplace`, but implementing Ozon accounting requires adding:

- parser strategies under `app/parsers/ozon/`
- ETL persist pipeline under `app/etl/ozon/`
- ledger mapping semantics + reconciliation rules
- tests and coverage recommendations

Until that exists, the coverage API will primarily reflect WB coverage.


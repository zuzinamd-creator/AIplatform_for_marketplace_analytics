# Real data validation (UX-2)

## Goal

Validate that the product UX works with real seller datasets:

- upload experience
- processing times and lifecycle visibility
- dashboard usefulness (operational-first)
- AI recommendation usefulness
- data quality edge cases and seller comprehension

## Fixtures and scenarios

Small non-sensitive fixtures live in `docs/product/fixtures/`.

Showcase scenarios are described in `docs/product/real_data_scenarios.md`.

## Validation harness (script)

Scripts:

- `scripts/ux2_real_data_validation.py` — upload, poll, costs, optional AI
- `scripts/product_validation_simulation.py` — daily/weekly/incident/growth workflow simulation (PRODUCT-VALIDATION)

Capabilities:

- registers/logins a demo seller
- uploads a report file
- polls status until processed/failed
- optionally imports costs
- optionally triggers an AI intelligence run

Example:

```bash
python scripts/ux2_real_data_validation.py \
  --report-file docs/product/fixtures/sample_report_placeholder.csv \
  --costs-file docs/product/fixtures/sample_costs.csv \
  --run-ai
```

Replace `sample_report_placeholder.csv` with a real WB/Ozon export for meaningful results.

## Data quality edge cases checklist

- empty file
- wrong delimiter / encoding
- duplicate upload (same checksum)
- oversized file (exceeds `MAX_UPLOAD_BYTES`)
- report schema drift (new columns)
- malformed xlsx/csv

## What to record during demos

- time to upload accepted
- time to reach `processed` / `failed`
- clarity of “what to do next”
- usefulness rating distribution for recommendations


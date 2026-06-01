# Realistic fixtures (UX-2)

These fixtures are **small, non-sensitive examples** intended to exercise:

- upload validation
- duplicate handling
- processing lifecycle visibility
- “problematic” edge cases

They are not intended to replicate full Wildberries/Ozon exports.

## Files

- `sample_costs.csv`: cost import example for `/api/v1/costs/import`
- `sample_report_placeholder.csv`: placeholder “report-like” CSV that should be replaced with real exports during demos

## Important

For real-world validation you should test using:

- recent Wildberries/Ozon exports (sanitized if needed)
- known-bad files (wrong delimiter, empty file, oversized file, corrupt xlsx)
- duplicate uploads (same checksum)


# Phase 9.17-E — Safe Incremental Stream v1 certification

## Pre-deploy fingerprint validation

| Item | Value |
|------|-------|
| Script | `scripts/validate_safe_incremental_stream_v1.py` |
| Tenant | `caefecb3-5789-4878-a9d4-929be573fbcc` |
| Window | 2026-07-06..2026-07-12 |
| Ledger rows | 40359 → filtered 30810 |
| Snapshots compared | 733 vs 733 |
| **Result** | **IDENTICAL** |

Domain stock math unchanged; Variant B ≡ legacy Python skip.

## Tests

- `test_safe_incremental_stream_v1.py` (carry-forward, hole-key, no-snapshot, late movement, predicate ≡ legacy)
- Existing inventory equivalence / reconstruction / rebuild-window suites — pass
- Unit suite (ignore pre-existing sku decimal module) — pass

## Performance (expected vs 9.17-C baseline)

| Stage | Before (Job A / Job B) | After (expected) |
|-------|------------------------|------------------|
| Inventory rebuild | 820 s / 112 s | Lower via SQL filter + DISTINCT ON + covering index |
| Phase 3 | ~5 s / ~199 s | Unchanged (out of scope) |
| Total ETL | ~14 min / ~6 min | Dominated by remaining Phase2/3 |

Measured production after numbers filled in post-deploy section.

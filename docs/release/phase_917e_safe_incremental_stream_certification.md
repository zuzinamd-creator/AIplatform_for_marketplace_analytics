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

## Performance (measured production — Phase 9.17-E1)

| Stage | Before (Job A / Job B) | After (A′ / B′) |
|-------|------------------------|----------------|
| Inventory rebuild | 820 s / 112 s | **79 s / 31 s** |
| Phase 3 | ~5 s / ~199 s | ~2 s / ~2 s* |
| Total ETL | ~14 min / ~6 min | **~1.4 min / ~1.6 min** |

\*Phase 3 on B′ is warm reprocess; inventory gains are the 9.17-E scope. Full evidence: [phase_917e1_production_performance_certification.md](phase_917e1_production_performance_certification.md).

## Verdict

**GO** — fingerprint IDENTICAL pre-deploy; production timings certified in 9.17-E1.

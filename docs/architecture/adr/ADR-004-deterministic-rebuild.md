# ADR-004: Deterministic inventory snapshot rebuild

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** LED-REPLAY-DET, SNAP-FP-DET, SNAP-FULL-EQ-INCR, OPS-REBUILD-IDEMP

## Context

Derived snapshots must be reproducible for drift detection, audits, and incremental vs full equivalence. Nondeterministic ordering or semantics fallback breaks trust.

## Decision

- Replay ledger in fixed order (see ADR-005).
- Classify movements with `SEMANTICS_REGISTRY[row.semantics_version]` — no silent default to current parser.
- Fingerprints exclude timestamps (`snapshot_state_fingerprint`).
- Incremental rebuild with full window + correct carry-forward must match full replay fingerprints.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Reuse prior snapshot rows without replay | Drift if ledger corrected; violates ledger authority |
| Float intermediates | Rounding drift across machines |
| “Best effort” semantics on unknown version | Misclassified operations; regulatory/audit risk |
| Non-idempotent rebuild (cache partial state) | Second rebuild differs without ledger change |

## Tradeoffs

- **Pros:** Testable; drift verification meaningful; safe AI refactors when tests hold.
- **Cons:** Must version semantics explicitly; registry maintenance overhead.

## Operational impact

- Semantics upgrades require planned rebuild (ADR-007), not hot inline mutation.
- Benchmark suite proves idempotent full rebuild on large synthetic tenants.

## Failure scenarios

- Changed fingerprint fields without updating tests → false drift alerts.
- Wrong carry-forward date → incremental ≠ full (caught by equivalence tests).

## Enforcement

- Domain: `InventorySnapshotPipeline`, `snapshot_fingerprint.py`
- Tests: `test_snapshot_fingerprint.py`, `test_full_incremental_rebuild_equivalence.py`, `test_inventory_rebuild_benchmark.py`

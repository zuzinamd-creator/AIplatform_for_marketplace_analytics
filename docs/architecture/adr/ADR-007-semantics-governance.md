# ADR-007: Semantics versioning and lifecycle governance

**Status:** Accepted  
**Date:** 2026-05  
**Invariants:** SEM-NO-SILENT-FALLBACK, SEM-INVALID-NO-INLINE, SEM-LIFECYCLE

## Context

WB operation labels change. Historical ledger rows must keep classification frozen at ingest time. New parser versions must not silently reclassify old rows.

## Decision

- Store `semantics_version` on normalized and ledger rows.
- `assert_ingest_allowed` / `assert_rebuild_allowed` gate ingest and replay.
- `SEMANTICS_REGISTRY[version]` resolves classification — raises `UnsupportedSemanticsVersionError` if missing.
- Semantics invalidation **queues** `snapshot_rebuild_requirements`; does **not** rebuild inline on API path.

## Alternatives considered

| Alternative | Why rejected |
|-------------|--------------|
| Always use latest parser for replay | Historical reports change meaning retroactively |
| Silent fallback to default strategy | Violates SEM-NO-SILENT-FALLBACK; audit failure |
| Inline rebuild on version disable | API latency; lock contention with ETL (ADR-002) |
| Per-row runtime plugin discovery | Nondeterministic without strict registry |

## Tradeoffs

- **Pros:** Auditable versioning; explicit migration path for new semantics.
- **Cons:** Registry + lifecycle table maintenance; rebuild backlog on breaking changes.

## Operational impact

- Deprecate versions via `semantics_lifecycle_versions` before disable.
- Run full/incremental rebuild after semantics change (queued worker).

## Failure scenarios

- Ingest while version disabled → hard fail (desired).
- Rebuild without registry entry → fail fast (desired).

## Enforcement

- `governance_policy.py`, `semantics_registry.py`, `SemanticsInvalidationService`
- Tests: `test_semantics_governance_*.py`

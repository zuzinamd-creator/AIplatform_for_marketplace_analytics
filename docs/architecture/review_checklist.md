# Architecture review checklist

Use before merging changes that touch ETL, inventory, queue, semantics, or migrations.

## Core contracts

- [ ] [Invariants](invariants.md) preserved (list IDs in PR description)
- [ ] Relevant [ADRs](adr/README.md) read; updated if decision changed
- [ ] [Boundaries](boundaries.md) respected (txn, layer, tenant)

## Data plane

- [ ] Ledger remains append-only (no UPDATE/DELETE paths)
- [ ] Replay order unchanged or ADR-005 updated
- [ ] Fingerprints deterministic (`test_snapshot_fingerprint.py`)
- [ ] Full vs incremental equivalence still holds if rebuild touched

## Concurrency & visibility

- [ ] Advisory locks preserved (`pg_try_advisory_xact_lock`, fail-fast)
- [ ] Full promote remains single-transaction (ADR-003)
- [ ] Queue uses `SKIP LOCKED` on claim (ADR-006)
- [ ] No silent semantics fallback (ADR-007)

## Multi-tenant & security

- [ ] Tenant isolation via RLS / `TenantSession` (no new bypass)
- [ ] Rebuild lock scoped per `user_id`
- [ ] Queue broker uses `QueueSession` only for `etl_jobs`

## Operations

- [ ] Anomaly persist still separate txn from ledger (ADR-008)
- [ ] Drift verification remains read-only if touched
- [ ] WAL amplification acceptable for large promote (note in PR if full rebuild changed)
- [ ] Structured logs/metrics added for new failure modes

## Tests & docs

- [ ] `pytest tests/unit` pass
- [ ] `pytest tests/integration -m integration` pass (if applicable)
- [ ] Benchmark rerun if required ([ai_change_policy.md](ai_change_policy.md) §2)
- [ ] README updated (migrations, invariants, ops notes)
- [ ] `python scripts/architecture_governance_check.py` pass
- [ ] [dependency_rules.md](dependency_rules.md) — no new forbidden layer imports
- [ ] [extension_contracts.md](extension_contracts.md) — extension type identified (marketplace / ETL / semantics / rebuild / AI)

## AI-generated changes (extra)

- [ ] No forbidden patterns from [ai_change_policy.md](ai_change_policy.md) §5
- [ ] No “simplification” that merges transactions or removes locks
- [ ] No new `float` money paths in domain

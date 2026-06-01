# Release checklist

Use before tagging a production release. All items must pass or be explicitly waived with owner sign-off.

## Schema & migrations

- [ ] `alembic upgrade head` on clean DB and on staging snapshot
- [ ] Downgrade script reviewed (if provided) — no ledger table drops
- [ ] RLS policies unchanged or migration-reviewed for tenant isolation
- [ ] `0012` orchestration columns present if rebuild ops enabled

## Determinism & replay

- [ ] **Replay equivalence validated:** incremental vs full rebuild produce identical snapshot fingerprints for benchmark fixtures
- [ ] Semantics version on draft matches promoted snapshot version
- [ ] No change to advisory lock namespace / try-lock behavior without ADR

## Automated tests

- [ ] `pytest tests/unit -q`
- [ ] `pytest tests/integration -m integration` (exclude stress unless noted)
- [ ] `RUN_STRESS_TESTS=true` benchmarks rerun if ETL/rebuild/streaming touched
- [ ] `ruff check .` and `mypy app tests` on changed modules (full repo if time permits)

## Drift & integrity

- [ ] **Drift checks pass** on golden tenant fixtures (`snapshot_consistency_checks.is_consistent`)
- [ ] Invariant probes still log-only (`platform_invariant_violation` not firing in happy path)

## Queue lifecycle

- [ ] **Queue lifecycle validated:** enqueue → claim → ack / fail → visibility recover → dead_letter
- [ ] Worker still calls `recover_stale()` before `claim()`
- [ ] No new hidden retry loops in API paths

## Operations & recovery

- [ ] `TenantRecoveryService` primitives documented in [failure_modes.md](failure_modes.md)
- [ ] Safety guard log events unchanged or documented in [metrics_catalog.md](metrics_catalog.md)
- [ ] [disaster_recovery.md](disaster_recovery.md) playbooks still accurate

## Documentation

- [ ] **README updated** (failure recovery, safeguards, performance budgets, release governance)
- [ ] ADR added if architectural boundary crossed
- [ ] `scripts/architecture_governance_check.py` passes in CI

## Performance budgets

- [ ] [performance_budget.md](performance_budget.md) thresholds still met on reference hardware
- [ ] WAL warning threshold appropriate for target Postgres tier

## Sign-off

| Role | Name | Date |
|------|------|------|
| Engineering | | |
| Operations | | |

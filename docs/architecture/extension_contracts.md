# Extension contracts

How to extend the platform without breaking invariants. **Major behavioral changes require an ADR.**

## 1. New marketplace

| Requirement | Detail |
|-------------|--------|
| Parser package | `app/parsers/<marketplace>/` with strategies + semantics |
| ETL package | `app/etl/<marketplace>/` processor + persist |
| Pipeline route | Register in `ETLPipeline` / `Marketplace` enum |
| Models | Ledger tables or shared ledger with marketplace discriminator |
| Tests | Integration upload fixture + unit parser tests |
| ADR | If ledger shape or queue contract differs |

**Invariants:** LED-APPEND-ONLY, FIN-DECIMAL, tenant RLS on all new tables.

**Anti-corruption:** marketplace-specific columns stay in parser normalized types until mapped to domain drafts.

## 2. New ETL pipeline stage

| Requirement | Detail |
|-------------|--------|
| CPU vs DB | Parse/validate outside transaction |
| Idempotency | Define keys before persist |
| Failure | `fail()` / anomaly buffer — no silent drop |
| Observability | `operation_stage`, `record_metrics` |
| Tests | Integration with `db_isolation` |

**Forbidden:** merging anomaly persist into ledger txn (ADR-008).

## 3. New AI module

| Requirement | Detail |
|-------------|--------|
| Entry | `AIOrchestrationService` only — no direct LLM calls from API |
| Input contract | `AIInsightInputDTO` (`app/dto/analytics_dto.py`) |
| Agent | Register in `app/ai/agents.py` + `docs/ai/agent_model.md` |
| Prompt | `PromptRegistry` + [prompt_contracts.md](../ai/prompt_contracts.md) review |
| Policy | `assert_ai_action_allowed` for every tool |
| Data source | Read-only tools → services/ops — **not** raw ledger SQL |
| Mutations | `ai_insights` draft only if `may_persist_insight` |
| Audit | `ai_execution_runs` row per run (migration `0013`) |
| Tests | `tests/unit/test_ai_governance.py` + integration run lifecycle |
| Docs | [docs/ai/](../ai/ai_architecture.md) updated |

**Guarantee:** AI must not become a backdoor to rebuild or ledger mutation. See [ai_governance.md](../ai/ai_governance.md).

## 4. New analytics metric

| Requirement | Detail |
|-------------|--------|
| Computation | `app/domain/analytics` pure functions |
| Materialization | Optional table via migration + persist hook |
| API exposure | Schema in `app/schemas`, map in services |
| Decimal | No float money |
| Tests | Unit golden cases + integration if persisted |

## 5. New rebuild strategy

| Requirement | Detail |
|-------------|--------|
| ADR | Required (touches ADR-003/004/005) |
| Lock | `pg_try_advisory_xact_lock` per tenant |
| Ledger | Read-only |
| Equivalence | Fingerprint test vs incremental or full baseline |
| Benchmark | `RUN_STRESS_TESTS` for hot path |
| Orchestration | Update `RebuildOrchestrationService` states if async |

**Mandatory tests:**

- `test_rebuild_production_guarantees.py`
- `test_inventory_rebuild_locking.py`
- Unit fingerprint / replay order tests

## 6. New semantics version

| Requirement | Detail |
|-------------|--------|
| Registry | `SEMANTICS_REGISTRY` + lifecycle row migration |
| Policy | `governance_policy.assert_ingest_allowed` / `assert_rebuild_allowed` |
| Invalidation | `SemanticsInvalidationService.request_rebuild` |
| Rows | Freeze version on ledger/snapshot rows |
| Tests | Unknown version raises; disabled version blocked |
| ADR | Update ADR-007 if lifecycle rules change |

**Operational:** complete rebuild before enabling ingest on breaking versions.

## Extension checklist (all types)

- [ ] [invariants.md](invariants.md) reviewed
- [ ] [dependency_rules.md](dependency_rules.md) imports respected
- [ ] Integration tests added or extended
- [ ] README §18 if migration
- [ ] ADR if decision-level
- [ ] `architecture_governance_check.py` passes
- [ ] No hidden async side effects

## Governance requirements

| Change size | ADR | Benchmark | Integration |
|-------------|-----|-----------|-------------|
| Additive field / endpoint | No | No | Targeted |
| Queue / rebuild / RLS | Yes | If hot path | Full targeted suite |
| Semantics version | Yes | If replay changes | Rebuild + WB pipeline |
| New marketplace | Yes | If inventory scale | New marketplace suite |

Full policy: [ai_change_policy.md](ai_change_policy.md).

## Operational guarantees (must preserve)

- Deterministic replay (LED-REPLAY-*, SNAP-FP-DET)
- Staging promote atomicity (SNAP-PROMOTE-ATOMIC)
- Visibility recovery (Q-VIS-RECOVER)
- Explicit recovery (no hidden API retries)
- RLS tenant isolation (TEN-*)

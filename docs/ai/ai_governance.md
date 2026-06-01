# AI governance

## What AI may do

| Allowed | Mechanism |
|---------|-----------|
| Summarize `AIInsightInputDTO` metrics | Analytics/reporting agents |
| Investigate anomalies (read ops) | Anomaly agent + read tools |
| Draft `ai_insights` rows | Agents with `WRITE_AI_INSIGHT_DRAFT` |
| Read semantics/rebuild/queue status | Ops-backed read tools |
| Emit structured audit logs | `ai_execution_runs`, `emit_ai_metric` |

## What AI must NEVER do

| Forbidden | Policy action |
|-----------|---------------|
| Insert/update/delete ledger rows | `MUTATE_LEDGER` |
| Hand-edit snapshots | `MUTATE_SNAPSHOT` |
| Call `FullInventoryRebuildService` / dispatcher | `TRIGGER_REBUILD` |
| Claim or ack `etl_jobs` | `ENQUEUE_ETL` |
| Bypass RLS or semantics | `BYPASS_*` |
| Generate KPIs from disabled semantics | Context gate |
| Auto-replay dead letters | Requires human + `TenantRecoveryService` |

## Deterministic vs probabilistic boundaries

| Deterministic (platform-owned) | Probistic (AI-owned, labeled) |
|-------------------------------|--------------------------------|
| Ledger replay, aggregates | Narrative summary |
| `AIInsightInputDTO` numbers | Root-cause hypothesis |
| Anomaly counts from DB | Recommendations |
| Semantics version checks | Executive tone / phrasing |

Prompt contracts declare `deterministic_sections` vs `probabilistic_sections` — see [prompt_contracts.md](prompt_contracts.md).

## Approval requirements

| Action | Approval |
|--------|----------|
| Persist insight draft | Agent permission + valid context |
| Financial commitment language | Human (`requires_human_approval_for`) |
| Trigger rebuild / DLQ replay | Platform operator |
| New prompt version | Prompt review checklist |
| New agent kind | ADR + extension contract |

## Observability & auditability

- Correlation id on each run
- Tool calls appended to `audit_events` JSONB
- Log events: `ai_run_started`, `ai_tool_call`, `ai_run_completed`, `ai_run_failed`
- Token and duration budgets enforced in `ExecutionTrace`

## Operational safeguards

- `AI_ENABLED` global kill switch
- Degraded mode when rebuild running or backlog high
- `ai_context_invalid` when semantics unsupported
- No hidden retries on AI runs (explicit `fail_run`)

## Alignment with platform governance

- [docs/architecture/invariants.md](../architecture/invariants.md)
- [docs/architecture/ai_change_policy.md](../architecture/ai_change_policy.md)
- [docs/architecture/extension_contracts.md](../architecture/extension_contracts.md) §3

# AI operations

## Metrics (structured logs)

| Event | When |
|-------|------|
| `ai_run_started` | `begin_run` committed |
| `ai_run_completed` | Successful completion |
| `ai_run_failed` | Policy or execution error |
| `ai_tool_call` | Each governed tool invocation |
| `ai_context_invalid` | Semantics gate failed |
| `ai_context_degraded_rebuild_running` | Rebuild in flight |
| `ai_context_stale_data_warning` | Rebuild backlog high |

## Token usage

Tracked on `ai_execution_runs.tokens_used` vs `token_budget`.

Aggregate in log pipeline: sum `tokens_used` by `agent_kind` / tenant.

## Execution failures

Query:

```sql
SELECT id, agent_kind, last_error, created_at
FROM ai_execution_runs
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 50;
```

(Tenant-scoped via RLS in application.)

## Degraded-mode behavior

When `degraded_mode=true`:

- Run may complete with status `degraded`
- UI should show: “Inventory rebuild in progress — narrative may be stale”
- Deterministic DTO sections still valid if `context_valid`

## Disable modes

| Switch | Effect |
|--------|--------|
| `AI_ENABLED=false` | All `begin_run` rejected |
| Per-tenant (future) | Feature flag in services layer |

## Extension requirements

New AI modules must provide:

- Prompt contract + review
- Agent permissions row
- Policy unit tests
- Integration test for run audit row
- Ops log event list update (this doc)

See [ai_architecture.md](ai_architecture.md) and [../architecture/extension_contracts.md](../architecture/extension_contracts.md).

## Safety checklist (release)

- [ ] No new forbidden imports (`app/ai` → `app/etl.wb`)
- [ ] `architecture_governance_check.py` passes
- [ ] AI policy tests pass
- [ ] Migration `0013` applied in staging
- [ ] `AI_ENABLED` documented for incident response

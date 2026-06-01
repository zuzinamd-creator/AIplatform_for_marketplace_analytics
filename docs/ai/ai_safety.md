# AI safety

Safety primitives in `app/ai/safety.py` and `app/ai/orchestration.py`.

## Execution tracing

`ExecutionTrace` records:

- `run_id`, `agent`, `prompt_id`, `prompt_version`
- Per-tool call log (`tool`, `status`, `at`)
- `tokens_used`, `elapsed_ms`

Persisted to `ai_execution_runs.audit_events` on complete/fail.

## Tool-call logging

Each invocation: log event `ai_tool_call` with `tool`, `status`, `agent`.

Policy checked **before** recording (`ExecutionSafetyEnforcer`).

## Budgets

| Budget | Source |
|--------|--------|
| Token budget | `AgentPermissions.token_budget` |
| Tool calls | `AgentPermissions.max_tool_calls` |
| Wall clock | `AI_EXECUTION_TIMEOUT_SECONDS` |

Violation → `AIPolicyViolation` at `assert_within_budget()`.

## Retry boundaries

- AI runs do **not** auto-retry on failure
- Caller may start a **new** run with new `run_id`
- ETL/orchestration retries remain separate systems

## Failure isolation

- AI failure does not abort ETL worker or rebuild dispatcher
- `fail_run()` commits audit row with `last_error`
- Partial tool calls remain in audit trail

## Timeout controls

`ExecutionTrace.elapsed_ms()` compared to `settings.ai_execution_timeout_seconds`.

Future async LLM calls should use `asyncio.wait_for` with same limit.

## Prompt versioning

Immutable `PromptContract` per `prompt_id`; version stored on run row for replay/debug.

## Hallucination-risk boundaries

| Risk | Mitigation |
|------|------------|
| Invented KPIs | Probabilistic sections only; numbers from DTO |
| Wrong semantics | `context_valid` gate |
| Stale inventory | Degraded mode if rebuild running |
| Confident remediation | `requires_human_approval_for` categories |

## Disable / fallback modes

| Mode | Behavior |
|------|----------|
| `AI_ENABLED=false` | `begin_run` raises immediately |
| `context_valid=false` | No insight input passed to model |
| `degraded_mode=true` | Run status `degraded`; UI shows warning |
| Provider outage | Caller catches; `fail_run` — no platform mutation |

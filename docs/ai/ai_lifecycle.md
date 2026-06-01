# AI execution lifecycle

## States

| Status | Meaning |
|--------|---------|
| `requested` | Run row created |
| `running` | Context validated, provider call in flight |
| `succeeded` | Completed with valid context |
| `degraded` | Completed under stale/rebuild pressure |
| `failed` | Provider or validation error |
| `cancelled` | Operator cancelled (reserved) |

## Flow

1. **Gate** — `AI_ENABLED`, rate limit, agent kill switch (`AI_DISABLED_AGENTS`).
2. **Policy** — `assert_ai_action_allowed`, workflow/prompt match.
3. **Context** — `AIContextAssembler` + `build_grounded_context` (semantics, rebuild counts).
4. **Memory** — load bounded `ai_session_turns` (non-authoritative).
5. **Provider** — `LLMAdapter.complete` via factory (mock default).
6. **Validate** — `validate_insight_output` (confidence, stale, unsupported claims).
7. **Persist** — advisory `ai_insights` draft when agent permits.
8. **Audit** — `ai_execution_runs` row finalized with tokens, duration, tool calls.

## API entrypoints

- `POST /api/v1/ai/runs` — start workflow run
- `GET /api/v1/ai/runs` — paginated audit list
- `GET /api/v1/ai/runs/{id}` — run detail
- `GET /api/v1/ai/executions/{id}` — alias for run detail
- `GET /api/v1/ai/insights` — paginated advisory insights

## Invariants

- No ledger/snapshot mutation.
- No rebuild/queue trigger from AI path.
- Outputs labeled `advisory_only` in insight payload.

## Provider Integration (REAL-AI-1)

Goal: run real OpenAI-compatible LLM calls while preserving:

- governance + policy checks
- RLS tenant isolation
- auditable run lifecycle (`AIExecutionRun`)
- advisory-only outputs (no ledger mutation)

### Configuration

Environment variables:

- `AI_PROVIDER` = `mock` | `openai_compatible`
- `AI_FAILOVER_PROVIDER` (optional)
- `AI_OPENAI_BASE_URL`
- `AI_OPENAI_API_KEY`
- `AI_OPENAI_MODEL`
- `AI_REQUEST_TIMEOUT_SECONDS`
- `AI_MAX_RETRIES`

### Provider selection + failover

`app/ai/providers/factory.py:get_llm_adapter()`:

- circuit breaker gate: `GLOBAL_CIRCUIT_BREAKERS.allow("ai_provider")`
- primary provider: `settings.ai_provider`
- optional fallback: `settings.ai_failover_provider`
- bounded retries are handled by `app/ai/providers/retry.py`

### OpenAI-compatible adapter

`app/ai/providers/openai_compatible.py`

- `complete()` calls `POST {base_url}/chat/completions`
- `stream()` supports SSE streaming (`stream=true`, `stream_options.include_usage=true` when supported)


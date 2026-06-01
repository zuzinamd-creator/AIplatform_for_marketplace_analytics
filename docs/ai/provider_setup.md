# AI Provider Setup (REAL-AI-V4A)

## Supported providers

All providers use the **OpenAI-compatible** HTTP API (`/chat/completions`):

| `AI_PROVIDER` | Default base URL |
|---------------|------------------|
| `mock` | No network (dev/demo) |
| `openai` | `https://api.openai.com/v1` |
| `openrouter` | `https://openrouter.ai/api/v1` |
| `deepseek` | `https://api.deepseek.com` |
| `together` | `https://api.together.xyz/v1` |
| `ollama` | `http://localhost:11434/v1` |
| `openai_compatible` | Use `AI_OPENAI_BASE_URL` explicitly |

## Required variables

```env
AI_PROVIDER=openrouter
AI_OPENAI_API_KEY=sk-...
AI_OPENAI_MODEL=openai/gpt-4o-mini
```

Override base URL when needed:

```env
AI_OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

## Failover

```env
AI_FAILOVER_PROVIDER=deepseek
AI_FAILOVER_API_KEY=...
AI_FAILOVER_BASE_URL=https://api.deepseek.com
AI_FAILOVER_MODEL=deepseek-chat
```

Resolution order: primary → failover → mock (degraded). Circuit breaker may force mock when unhealthy.

## Model routing

```env
AI_REASONING_MODEL=...   # executive / causal / anomaly workflows
AI_FAST_MODEL=...        # streaming + short summaries
AI_CHEAP_MODEL=...       # embeddings (future)
```

## Cost caps

```env
AI_ENABLE_COST_TRACKING=true
AI_MAX_COST_PER_RUN_USD=0.50
AI_MAX_COST_PER_DAY_USD=25.00
```

Runs exceeding caps raise `AIPolicyViolation` (advisory layer blocked, no ledger impact).

## Prompt runtime

```env
AI_PROMPT_RUNTIME_VERSION=v3
```

`v1` retains legacy templates; `v3` uses governed analytical contracts in `app/ai/prompts/v3/`.

## Ops endpoints

- `GET /api/v1/ai/costs`
- `GET /api/v1/ai/providers/status`
- `GET /api/v1/ai/usage` (token summary)

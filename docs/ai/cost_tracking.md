## Token + Cost Tracking (REAL-AI-1)

This phase adds **token accounting** and **estimated cost** persistence per run.

### Persisted fields

Table: `ai_execution_runs` (nullable additive columns)

- `provider_name`
- `model_name`
- `prompt_tokens`
- `completion_tokens`
- `estimated_cost`

Migration: `alembic/versions/0019_ai_usage_cost_tracking.py`

### Cost estimation

Module: `app/ai/providers/pricing.py`

- `estimate_cost_usd(model, prompt_tokens, completion_tokens)` returns an estimate using a small pricing map.

### API

- `GET /api/v1/ai/usage?start=YYYY-MM-DD&end=YYYY-MM-DD`

Returns totals and a provider breakdown (tenant-scoped).


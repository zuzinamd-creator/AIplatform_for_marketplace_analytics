# Prompt Contracts v2

Registry: `app/ai/prompts/contracts_v2/registry.py`

Each contract includes:

- `prompt_id`, `version`
- `analyst_id`
- `purpose`
- `input_schema` / `output_schema` (Pydantic DTO names)
- `evaluation_examples` (JSON snippets for regression)
- `metadata` (`layer`, `advisory_only`)

## IDs

- `analyst.sales.v2`
- `analyst.ads.v2`
- `analyst.funnel.v2`
- `analyst.inventory.v2`
- `analyst.marketplace.v2`
- `analyst.anomaly.v2`
- `executive.aggregate.v2`

## Evaluation

`app/ai/evaluation/multi_layer_suite.py` — deterministic checks (no LLM required for CI).

Run in tests: `tests/unit/test_multi_layer_intelligence.py`

# Prompt Evaluation (v3)

## Suite

`app/ai/evaluation/prompt_v3_suite.py`

| Case | Validates |
|------|-----------|
| `governance_rules` | v3 system prompt includes anti-hallucination rules |
| `stale_data` | Degraded context reduces confidence |
| `unsupported_claims` | Claims without metrics flagged |
| `usefulness_payload` | Seller usefulness fields populated |
| `prioritization_rules` | Severity/prioritization in template |

## Run

```bash
pytest tests/unit/test_prompt_v3_runtime.py -q
```

## Regression with multi-layer

Also run:

```bash
pytest tests/unit/test_multi_layer_intelligence.py -q
```

## Adding fixtures

1. Add contract in `app/ai/prompts/v3/registry.py`
2. Map workflow in `_WORKFLOW_MAP`
3. Add eval function in `prompt_v3_suite.py`
4. Document rollback target (`rollback_target` field)

## Rollback

Set `AI_PROMPT_RUNTIME_VERSION=v1` or deactivate prompt (`active=False`) and rely on `rollback_target` v1 prompt id in governance registry.

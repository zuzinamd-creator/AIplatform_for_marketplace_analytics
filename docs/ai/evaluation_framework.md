# AI evaluation framework

## Goals

- Deterministic regression without live provider calls (default `AI_PROVIDER=mock`).
- Prompt contract coverage via `EvalCase` + `MockEvaluationAdapter`.
- Hallucination heuristics in `validate_insight_output` unit tests.

## Components

| Piece | Location |
|-------|----------|
| Eval runner | `app/ai/evaluation/runner.py` |
| Provider eval adapter | `app/ai/providers/mock.py` |
| Prompt regression tests | `tests/unit/test_ai_prompt_regression.py` |
| Validation tests | `tests/unit/test_ai_validation.py` |
| Engine integration | `tests/integration/test_ai_analytics_api.py` |

## Adding a case

```python
EvalCase(
    prompt_id="analytics.summary.v1",
    expected_contains=("advisory", "semantics"),
    sample_output="<model json>",
)
```

## CI recommendation

1. `pytest tests/unit/test_ai_*.py -q`
2. `pytest tests/integration/test_ai_*.py -m integration`
3. Optional: `AI_PROVIDER=openai_compatible` smoke in staging only.

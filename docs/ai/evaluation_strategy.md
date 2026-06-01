# AI Evaluation Strategy

Phase B extends evaluation with intelligence fixtures (`app/ai/evaluation/benchmarks.py`).

## Suites

| Suite | Location | Purpose |
|-------|----------|---------|
| Prompt regression | `tests/unit/test_ai_prompt_regression.py` | Contract stability |
| Intelligence eval | `INTELLIGENCE_EVAL_CASES` | Deterministic replay checks |
| Decision / multi-agent | `test_ai_decision_engine.py`, `test_ai_multi_agent.py` | Scoring and coordination |
| Integration | `test_ai_intelligence_api.py` | End-to-end persistence |

## Replay model

Eval cases use `sample_output` JSON and `expected_contains` — no live LLM required in CI when `AI_PROVIDER=mock`.

## Quality benchmarks

Recommendation quality is measured by: validation pass rate, contradiction count, confidence distribution, and operator feedback ratings.

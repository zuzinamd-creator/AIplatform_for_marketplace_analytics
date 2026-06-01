# AI Decision Engine

Phase B adds a deterministic decision layer (`app/ai/decision/engine.py`) on top of validated insights.

## Capabilities

| Engine | Role |
|--------|------|
| Recommendation scoring | Maps validated insight → `ScoredRecommendationDTO` |
| Prioritization | Workflow-aware priority (risk/anomaly boosted) |
| Revenue opportunity | Heuristic score for revenue/recommendation workflows |
| Risk classification | Unsupported claims, degraded context, workflow type |
| Approval gates | Human approval for pricing and high-risk classes |

## Constraints

- Advisory-only; never writes ledgers.
- Scoring is deterministic given validated input + grounded context.
- LLM output is consumed only after `validate_insight_output`.

## Data flow

```
ValidatedInsightDTO + GroundedContextDTO → AIDecisionEngine.score_recommendation() → ScoredRecommendationDTO
```

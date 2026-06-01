# AI Explainability

Explainability is built by `app/ai/explainability/builder.py` and persisted on `ai_recommendations`.

## Artifacts

| Artifact | Description |
|----------|-------------|
| Evidence graph | Nodes from `GroundedContextDTO.evidence` |
| Reasoning trace | Per-agent steps with confidence contributions |
| Operator summary | Plain-language summary for operators |
| Confidence rationale | Why confidence was assigned |
| Provenance | Run ID, insight ID, semantics version |
| Freshness score | Derived from grounding freshness |

## API

`GET /api/v1/ai/recommendations/{id}/explainability` returns stored explainability for audit and operator review.

## Maturity

Evidence is only as complete as grounding retrieval. High confidence without evidence triggers validator contradictions.

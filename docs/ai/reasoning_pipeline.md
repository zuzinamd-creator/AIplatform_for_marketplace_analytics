# AI Reasoning Pipeline (Multi-Layer v2)

## Lifecycle

1. **Deterministic KPI layer** — ETL → aggregates → `AIInsightInputDTO`
2. **Context assembly** — `AIContextAssembler` + semantics governance
3. **Grounding** — `build_grounded_context` + evidence refs
4. **LLM insight (optional path)** — `AIAnalyticsEngine` produces `ValidatedInsightDTO` (advisory narrative)
5. **Multi-layer pipeline** — `run_multi_layer_pipeline` → domain analysts → executive aggregation
6. **Coordinator enrichment** — `enrich_intelligence_result` merges executive output into recommendation + explainability
7. **Quality & policy** — `apply_quality`, `classify_and_gate`
8. **Persistence** — `reasoning_trace` JSON with `multi_layer` and `domain_insights`

## Trace structure

```json
{
  "steps": [...],
  "agent_messages": [...],
  "multi_layer": {
    "architecture_version": "2.0",
    "domain_outputs": [...],
    "executive": {...},
    "conflict_resolution": [...],
    "confidence_propagation": {...}
  },
  "domain_insights": [...]
}
```

## Constraints

- AI does not compute raw metrics from source files
- Financial authority remains in deterministic analytics
- All recommendations remain advisory and auditable

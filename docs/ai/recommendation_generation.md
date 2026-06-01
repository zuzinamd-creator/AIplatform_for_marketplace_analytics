# Recommendation Generation (Multi-Layer)

## Flow

`AIIntelligenceEngine.run_intelligence`:

1. `AIAnalyticsEngine.execute` — audited LLM run + validated insight
2. `MultiAgentCoordinator.coordinate` — action plan, scoring, explainability baseline
3. `run_multi_layer_pipeline` — six domain analysts + executive aggregation
4. `enrich_intelligence_result` — merge bullets, confidence, evidence graph, reasoning steps
5. `apply_quality` — fingerprint, impact copy, fatigue controls
6. `_persist_recommendation` — `reasoning_trace_payload` stores full multi-layer trace

## Seller-facing fields

| Field | Source |
|-------|--------|
| `title` / `summary` | Validated insight + executive narrative |
| `action_plan` | Planner + quality enrichments |
| `confidence_score` | Blended coordinator + executive confidence |
| `priority_score` | Decision engine + executive impact boost |
| `evidence_graph` | Grounded evidence + domain insight nodes |
| `reasoning_trace.domain_insights` | Per-analyst prioritized findings |

## Frontend

Recommendation detail page renders `domain_insights` with analyst label, confidence, severity, evidence refs, and priority rank.

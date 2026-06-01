# Prompt Topology Analysis (REAL-AI-2)

## Current topology (pre v2)

```
AIRunRequest → AIAnalyticsEngine.execute
  → render_prompt(grounded, workflow)  [single system+user template]
  → LLM provider (OpenAI-compatible / mock)
  → validate_insight_output → ValidatedInsightDTO
  → MultiAgentCoordinator
      Planner → generic Analyst (AIDecisionEngine) → Validator → Ops Advisor
  → recommendation_quality → persist AIRecommendation
```

### Prompt registry (v1)

| prompt_id | Role |
|-----------|------|
| `analytics.summary.v1` | Report KPI summary |
| `anomaly.investigation.v1` | ETL anomaly narrative |
| `inventory.insight.v1` | Inventory advisory |
| `forecast.prep.v1` | Forecast prep |
| `reporting.executive.v1` | Executive narrative |

Contracts live in `app/ai/prompts/registry.py` with coarse `deterministic_sections` / `probabilistic_sections` flags.

## Weaknesses

1. **Single-stage LLM** — One prompt + one validation path for all business domains (sales, ads, funnel, inventory, marketplace, anomalies).
2. **Generic “analyst”** — `MultiAgentCoordinator` uses `AIDecisionEngine` scoring, not domain-specialized reasoning.
3. **No structured domain outputs** — Findings are not required to include `evidence_refs`, `severity`, or per-analyst `recommended_actions`.
4. **Missing prompt specialization** — No per-domain input/output JSON schema or evaluation fixtures per analyst.
5. **Weak conflict handling** — Contradictions detected only at recommendation validator, not across domain findings.
6. **Limited trace granularity** — `reasoning_trace` stores planner/validator steps, not domain outputs or executive aggregation notes.
7. **Grounding gap** — Intelligence path historically assembled context without `insight_input`, weakening `metrics_snapshot` in grounded context.

## Target topology (v2)

```
ValidatedInsightDTO + GroundedContextDTO + AIInsightInputDTO
  → AnalyticalIntelligencePackage (slices only — no KPI computation)
  → 6× DomainAnalyst (structured DomainAnalystOutputDTO)
  → ExecutiveIntelligenceAggregator
  → enrich coordinator result + MultiLayerReasoningTraceDTO
  → persist reasoning_trace.multi_layer + domain_insights
```

LLM v1 prompts remain for narrative insight generation; **domain authority** stays on deterministic DTOs. Domain analysts in v2 are **deterministic interpreters** with versioned prompt contracts for future LLM-backed implementations.

## Where specialization was missing

| Domain | v1 coverage | v2 analyst |
|--------|-------------|------------|
| Sales / revenue | `analytics.summary.v1` | `SalesAnalyst` |
| Ads | none | `AdsAnalyst` |
| Funnel / concentration | implicit in summary | `FunnelAnalyst` |
| Inventory | `inventory.insight.v1` | `InventoryAnalyst` |
| Marketplace compare | none | `MarketplaceComparisonAnalyst` |
| Anomalies | `anomaly.investigation.v1` | `AnomalyAnalyst` |
| Executive merge | `reporting.executive.v1` | `ExecutiveIntelligenceAggregator` |

## Governance preserved

- KPIs sourced from `AIInsightInputDTO` / analytics layer only
- All outputs `advisory_only`
- Audit via `ai_execution_runs`, `reasoning_trace`, prompt contract versions

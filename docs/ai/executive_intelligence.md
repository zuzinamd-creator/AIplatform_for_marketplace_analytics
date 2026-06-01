# Executive Intelligence Layer

`ExecutiveIntelligenceAggregator` (`app/ai/executive/aggregator.py`) sits above domain analysts.

## Responsibilities

1. **Merge** — Flatten findings from all six domain outputs
2. **Resolve contradictions** — When opposing `recommended_actions` share evidence refs, retain higher-confidence finding
3. **Prioritize** — Rank by `severity_weight × confidence`
4. **Business impact** — Heuristic label (`elevated` / `moderate` / `low`)
5. **Narrative** — Seller-facing summary from top insights
6. **Final recommendations** — Deduplicated action list (max 15)

## Output

`ExecutiveAggregationResultDTO` with `prioritized_insights`, `conflicts_resolved`, `confidence_propagation`, and `domain_outputs` copy for audit.

## Contract

`executive.aggregate.v2` in `PromptContractRegistryV2`.

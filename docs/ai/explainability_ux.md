## Explainability UX (AI-USEFULNESS)

Goal: make every recommendation understandable as:

- **What to do** (recommended action)
- **Why it matters** (business impact / risk)
- **What evidence supports it** (evidence references)
- **How trustworthy it is** (confidence rationale + stale/degraded cues)

### UX principles

- **Evidence-first**: show concrete evidence references before reasoning text dumps.
- **Stale-aware**: reduce urgency language and confidence when data is stale/degraded.
- **Seller-language**: avoid backend terms (rebuild orchestration, ledgers, etc.) in the primary recommendation surface.

### Current implementation

- Backend stores explainability artifacts per recommendation:
  - `evidence_graph` (nodes + edges)
  - `reasoning_trace` (steps)
  - plus `action_plan.why_this_matters` and `action_plan.recommended_action`
- Frontend `RecommendationDetailPage` renders:
  - a concise “Why this matters” and “Suggested action” (from `action_plan` when present)
  - a readable evidence list (node cards) instead of only raw JSON
  - still keeps raw reasoning trace JSON available for deeper inspection

### What sellers should understand

- **Evidence**: where the claim comes from (report, KPI snapshot, anomaly signal).
- **Trust**: whether the system was in degraded mode / stale data conditions.
- **Actionability**: what external action to take (pricing, inventory, ads) and how to confirm.


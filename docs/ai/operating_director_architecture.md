# Operating Director Architecture (Phase 6.3)

Multi-agent AI Operating Director — architectural scaffold and migration plan.

**Status:** scaffold only (`app/ai/director/`). Legacy `AIIntelligenceEngine` remains the production path.

---

## 1. Target architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ L0  Data Quality Auditor                                        │
│     coverage_v2, missing_blocks, confidence_penalty,            │
│     allowed_analysts / blocked_analysts                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ gate (no data → analyst skipped)
┌────────────────────────────▼────────────────────────────────────┐
│ L1  Domain Experts (8)                                          │
│     Sales | MP Economics | Unit Economics | Advertising         │
│     Product Card | Inventory | Tax | Operating Cost             │
│     Each sees ONLY its slice; returns ActionableFinding           │
└────────────────────────────┬────────────────────────────────────┘
                             │ findings only (no raw KPI)
┌────────────────────────────▼────────────────────────────────────┐
│ L2  Cross-Domain Analysts (3)                                   │
│     Growth | Profit | Risk                                      │
│     Input = L1 outputs                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│ L3  Executive Director                                          │
│     Seller Report: TOP conclusions, causes, risks, actions,     │
│     limitations — NO raw KPI access                             │
└─────────────────────────────────────────────────────────────────┘
```

### Current (MVP) vs target

| Current | Target |
|---------|--------|
| KPI Snapshot → LLM Coordinator → Recommendations | Auditor → Experts → Cross → Director → Report |
| `business_coverage` V1 block model (~50%) | `coverage_v2` dimension model (~25–35% pilot) |
| Executive = `ExecutiveIntelligenceAggregator` over legacy 10 analysts | Executive Director over gated experts + cross-domain |
| LLM writes seller text | LLM optional at L3 only; deterministic scaffold first |

---

## 2. Reusable modules (no rewrite needed)

| Module | Role in new architecture |
|--------|--------------------------|
| `app/ai/analysts/*` | L1 adapters via `domain_experts.py` |
| `app/ai/analysts/governed_signals.py` | Feeds coverage dimensions + expert slices |
| `app/ai/deep/period_insights.py`, `period_causes.py` | Deterministic findings → MP / Unit experts |
| `app/ai/coverage/business_coverage.py` | V1 reporting; keep for backward compat |
| `app/ai/director/coverage_v2.py` | L0 coverage score (primary going forward) |
| `app/ai/director/data_quality_auditor.py` | L0 gate |
| `app/ai/executive/aggregator.py` | Reference for conflict resolution; retire gradually |
| `app/ai/product/seller_intelligence.py` | Report persistence / action_plan shape |
| `app/ai/quality/recommendation_quality.py` | Fatigue, fingerprint, actionability |
| `app/ai/grounding/assembler.py` | metrics_snapshot assembly |
| `app/services/ai_service.py` | Period insight bundle + governed_extras |
| `app/dto/domain_analyst_dto.py` | Legacy DTOs; map to `ActionableFindingDTO` |

---

## 3. Requires refactoring (not now — planned)

| Area | Why |
|------|-----|
| `AIIntelligenceEngine` | Strangler: call `run_operating_director()` behind feature flag; LLM becomes optional L3 |
| `MultiAgentCoordinator` + `AIDecisionEngine` | Today LLM-scored; should consume Director report, not KPI |
| `enrich_intelligence_result()` | Overwrites summary with legacy executive narrative |
| `build_analytical_package()` | Split into per-expert slice builders (no shared monolith package) |
| `DomainAnalystId` enum | Align with `DomainExpertId`; deprecate funnel/marketplace_comparison |
| Frontend `RecommendationDetailPage` | Render Director sections (conclusions / causes / risks / actions) |
| `reasoning_trace` schema | Store `OperatingDirectorTraceDTO` alongside legacy multi_layer |

---

## 4. Migration risks

| Risk | Mitigation |
|------|------------|
| Dual pipeline divergence | Feature flag; shadow-run Director, compare audit metrics |
| Coverage V2 drops score → user trust | Explain formula in UI; show dimension breakdown |
| Blocked analysts → empty reports | Executive Director always emits limitations + upload priorities |
| LLM bypass re-introduces KPI echo | L3 contract: input schema excludes metrics_snapshot |
| Migration big-bang | Strangler fig per layer: L0 → L1 gate → L2 → L3 → disable legacy executive |
| Expert adapter drift | One registry map (`domain_experors.py`) + contract tests per expert |

---

## 5. Phased implementation plan

### Iteration 1 (done — scaffold)
- DTOs, Coverage V2, Data Quality Auditor, pipeline skeleton
- Domain expert adapters over existing analysts
- Cross-domain + Executive Director (deterministic)
- Unit tests

### Iteration 2 (1 sprint, no UX change)
- Shadow mode: run `OperatingDirectorPipeline` inside `AIIntelligenceEngine`, persist trace in `reasoning_trace`
- Wire Coverage V2 into `action_plan.business_coverage`
- Audit script compares V1 vs V2

### Iteration 3 (1 sprint)
- Feature flag `AI_OPERATING_DIRECTOR_REPORT=1`: prepend Director report to summary
- Disable legacy `ExecutiveIntelligenceAggregator` narrative when flag on
- Actionability gate: reject findings without `recommended_action`

### Iteration 4 (1 sprint — ads data)
- Advertising data ETL → `ad_spend_available`, impressions, CTR
- Enable `AdvertisingAnalyst` + `GrowthAnalyst` full synthesis
- Product Card stub → real card metrics

### Iteration 5 (1 sprint — inventory)
- Warehouse snapshots → `InventoryAnalyst` + `RiskAnalyst` OOS signals

### Iteration 6 (1 sprint — tax & opex)
- Manual/import tax & opex tables
- `ProfitAnalyst` full chain

### Iteration 7 (optional LLM L3)
- LLM rewrites Director report from structured JSON only (no KPI in prompt)

**Total: ~6–7 iterations** to full replacement; **2 iterations** to production-visible improvement without UX redesign.

---

## 6. What can ship now (no UX change)

1. Shadow-run pipeline in intelligence engine (trace only)
2. Coverage V2 in API `action_plan.business_coverage_v2`
3. Stricter `allowed_analysts` gating in legacy orchestrator
4. Audit metrics for blocked experts count
5. Unit + integration tests for scaffold

---

## 7. After ads / CTR / inventory connected

| Data source | Unlocks |
|-------------|---------|
| WB/Ozon ads spend | Advertising Expert, Growth cross-analyst, promotion dimension |
| Impressions / clicks | CTR dimension, Growth causal chains |
| Card CTR / conversion | Product Card Expert, Growth |
| Warehouse snapshots | Inventory Expert, Risk OOS |
| Tax imports | Tax Expert, Profit cross-analyst |
| Opex imports | Operating Cost Expert, Profit cross-analyst |

---

## 8. Business Coverage V2 formula

```
Coverage V2 = Σ(weight_i × completeness_i) / Σ(weight_i) × 100%

Dimensions (weights sum to 100):
  sales=10, price=8, promotion=12, ctr=8, conversion=8,
  inventory=10, marketplace_economics=12, cogs=12, tax=10, opex=10

completeness_i = (# available sub-signals) / (# expected sub-signals) ∈ [0, 1]
```

**Pilot example** (sales partial, MP economics partial, COGS partial, rest 0):

≈ **28–35%** (vs V1 block model **50%**)

Implementation: `app/ai/director/coverage_v2.py`

---

## 9. Actionability contract

Every analyst output uses `ActionableFindingDTO`:

- `finding`
- `root_cause`
- `impact_estimate`
- `recommended_action` (required, min length enforced)

Findings without action are rejected at adapter layer (`domain_experts.py`).

---

## 10. Integration hook (future)

```python
# app/ai/intelligence/engine.py (Iteration 2)
from app.ai.director.pipeline import run_operating_director

od_trace = run_operating_director(grounded=grounded, insight_input=insight_input)
# persist od_trace in reasoning_trace; optional: replace summary when flag enabled
```

Not enabled in production until Iteration 3 feature flag.

---

## File map (scaffold)

```
app/ai/director/
  dto.py                  # Layer DTOs
  coverage_v2.py          # Business Coverage V2
  data_quality_auditor.py # L0
  domain_experts.py       # L1 adapters
  cross_domain.py         # L2
  executive_director.py   # L3
  pipeline.py             # Orchestrator
```

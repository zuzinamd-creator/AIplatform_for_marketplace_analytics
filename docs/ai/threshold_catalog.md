# Threshold Catalog — AI & Intelligence Layer

**Version:** 1.0  
**Date:** 2026-06-07 (Phase 6.5.1)  
**Status:** Normative reference for MVP Hardening sensitivity analysis  
**Policy:** Thresholds are **deterministic constants** in code. Changes require re-audit per [ai_change_policy.md](../architecture/ai_change_policy.md).

---

## How to read this catalog

| Column | Meaning |
|--------|---------|
| **Threshold** | Named constant or magic number |
| **Value** | Current production value |
| **Purpose** | What decision it gates |
| **File** | Primary source module |
| **Rationale** | Why this value; calibration notes |

Phase 6.3.0B pilot calibration source: `reports/phase_630_inventory_audit.json` (4 reports, 1 user).

---

## 1. Inventory aging & risk

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| `SLOW_MOVER_THRESHOLD_DAYS` | 30 | SKU idle days → slow mover classification | `app/domain/inventory/intelligence.py` | Industry default for marketplace FBO; below dead stock threshold |
| `DEAD_STOCK_THRESHOLD_DAYS` | 60 | SKU idle days → dead stock | `app/domain/inventory/intelligence.py` | 2× slow mover; blocks turnover capital |
| `INVENTORY_RISK_ITEM_THRESHOLD` | 3 | Count of dead/slow SKUs → elevated risk severity | `app/domain/inventory/intelligence.py` | Avoid single-SKU noise; pilot had ≥3 dead stock hits |
| `STOCK_CONCENTRATION_HIGH` | 60% | Top-3 frozen capital share → medium risk / L2 finding | `app/domain/inventory/intelligence.py` | Capital concentration warning band |
| `FROZEN_CAPITAL_HIGH_SHARE` | 20% | Frozen capital / revenue → medium risk; L1 escalation input | `app/domain/inventory/intelligence.py` | Pilot: inventory findings triggered at ~20%+ revenue share |
| Frozen capital high risk | 30% | `inventory_risk_level = "high"` | `app/domain/inventory/intelligence.py` `_inventory_risk_level` | Escalated band above medium (20%) |
| Concentration high risk | 70% | Top-3 share → high risk level | `app/domain/inventory/intelligence.py` | Strong concentration = nеликвид risk |
| Concentration severity (analyst) | 70% | `inventory_stock_concentration` severity high vs medium | `app/ai/analysts/inventory.py` | Aligns with domain high-risk band |
| Inventory deep bullets cap | 4 | Max bullets in `inventory_deep_bullets()` | `app/domain/inventory/intelligence.py` | Prevent executive overload |

---

## 2. Priority engine & IQ escalation

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Revenue protection IQ gap | **+8.0 pp** | Inventory may become primary only if IQ > best revenue IQ + 8 | `app/ai/insights/priority_engine.py` `_select_primary_insight` | Phase 6.3.0B calibration; restored SU from 68.2 → 80.3 |
| `sales_top_sku` priority | L1 | Top revenue SKU always eligible for primary | `app/ai/insights/priority_engine.py` | Pilot periods always had a revenue leader; protects against inventory dominance |
| Inventory L1 escalation | `inventory_dead_stock` + severity high/critical | Dead stock → L1 | `app/ai/insights/priority_engine.py` | Critical capital lock |
| Inventory L1 escalation | `inventory_frozen_capital` + severity high | Frozen capital ≥20% rev → L1 | `app/ai/insights/priority_engine.py` | Matches `FROZEN_CAPITAL_HIGH_SHARE` |
| Default inventory findings | L2 | frozen (medium), concentration, risk, slow movers | `app/ai/insights/priority_engine.py` | Supporting domain, not primary by default |
| Executive lead max items | 3 | `pick_executive_lead(max_items=3)` | `app/ai/insights/priority_engine.py` | Seller-facing summary length |
| Max inventory slots in lead | 1 | Domain-balanced executive composition | `app/ai/insights/priority_engine.py` `_balanced_executive_lead` | Prevents inventory wall in summary |
| Deep bullet confidence L1 | 0.88 | Structured insight from deep period | `app/ai/insights/priority_engine.py` | Matches analyst confidence band |
| Deep bullet confidence L2 | 0.72 | Non-L1 deep bullets | `app/ai/insights/priority_engine.py` | Lower than governed findings |
| Causal headline confidence L1 | 0.88 | Period driver headline | `app/ai/insights/priority_engine.py` | High trust in governed comparison |

---

## 3. Seller usefulness weighting

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Usefulness dampening factor | **× 0.88** | `seller_usefulness_score = IQ.overall × 0.88` | `app/ai/product/seller_intelligence.py` | Conservative seller-facing score; 80.3 = 91.3 IQ × 0.88 approx |
| Priority score urgency high | ≥ 70 | `urgency_score = 75` | `app/ai/product/seller_usefulness.py` | Maps to "на этой неделе" |
| Priority score urgency medium | ≥ 40 | `urgency_score = 55` | `app/ai/product/seller_usefulness.py` | Standard attention |
| Priority score urgency low | < 40 | `urgency_score = 35` | `app/ai/product/seller_usefulness.py` | Informational |
| Urgency score cap (stale) | ≤ 45 | Degraded context lowers urgency | `app/ai/product/seller_usefulness.py` | Trust gating |
| Urgency label "сегодня" | ≥ 80 | Russian urgency string | `app/ai/product/seller_usefulness.py` | Seller action framing |
| Anomaly priority boost | +8.0 | Fatigue/prioritization boost | `app/ai/product/prioritization.py` | Elevate anomaly workflows |
| Recommendation fatigue cooldown | 3 days | `COOLDOWN_DAYS` — suppress repeat insights | `app/ai/product/fatigue.py` | Reduce alert fatigue |

---

## 4. Insight quality scoring (IQ)

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Causal depth max | 25.0 | IQ component cap | `app/ai/insights/quality.py` | 4-component model → 100 overall |
| Business relevance base | 8.0 | IQ base before priority bonus | `app/ai/insights/quality.py` | Floor for any insight |
| Business L1 bonus | +17.0 | Priority level 1 | `app/ai/insights/quality.py` | Primary insights score higher |
| Business L2 bonus | +10.0 | Priority level 2 | `app/ai/insights/quality.py` | Supporting insights |
| Business L3 bonus | +3.0 | Priority level 3 | `app/ai/insights/quality.py` | Informational |
| Actionability min length | 20 chars | Action text scoring | `app/ai/insights/quality.py` | Penalize vague actions |
| Confidence scale | × 25.0 | Maps 0–1 confidence to IQ points | `app/ai/insights/quality.py` | Linear confidence contribution |

---

## 5. Governed signals — revenue, logistics, returns, concentration

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| `REVENUE_DROP_THRESHOLD` | **-10%** | Period revenue delta → drop finding | `app/ai/analysts/governed_signals.py` | Material decline for seller action |
| `REVENUE_GROWTH_THRESHOLD` | **+10%** | Period revenue delta → growth finding | `app/ai/analysts/governed_signals.py` | Symmetric growth signal |
| Revenue drop severity high | ≤ -20% | Escalated severity on deep drop | `app/ai/analysts/revenue_change.py` | Critical decline band |
| `LOGISTICS_HIGH_SHARE` | **15%** | Logistics / revenue → high burden | `app/ai/analysts/governed_signals.py` | WB typical logistics band (~10–15%) |
| Logistics severity high | ≥ 20% | High severity on logistics share | `app/ai/analysts/logistics.py` | Above benchmark |
| `LOGISTICS_SKU_THRESHOLD` | **25%** | Per-SKU logistics share anomaly | `app/ai/analysts/governed_signals.py` | SKU-level outlier detection |
| Logistics share delta | ≥ 3 pp | Period-over-period logistics growth | `app/ai/analysts/logistics.py` | Trend signal |
| `RETURNS_HIGH_RATE` | **10%** | Return rate / revenue → high returns | `app/ai/analysts/governed_signals.py` | Margin erosion threshold |
| Returns severity high | ≥ 15% | Escalated return rate | `app/ai/analysts/returns.py` | Critical return band |
| Return rate delta | ≥ 3 pp | Period return rate growth | `app/ai/analysts/returns.py` | Trend signal |
| Return top SKU share | ≥ 8% | SKU-level return leader | `app/ai/analysts/returns.py` | Actionable SKU focus |
| `CONCENTRATION_TOP1` | **50%** | Top-1 SKU revenue share risk | `app/ai/analysts/governed_signals.py` | Single-SKU dependency |
| `CONCENTRATION_TOP3` | **70%** | Top-3 SKU revenue share risk | `app/ai/analysts/governed_signals.py` | Portfolio concentration |
| Concentration severity high | ≥ 67% | Top-1 high severity | `app/ai/analysts/concentration.py` | Near-monopoly SKU |
| Revenue driver materiality | ≥ 1000 ₽ | SKU driver in revenue change | `app/ai/analysts/revenue_change.py` | Ignore noise amounts |
| Sales low margin | < 0.15 (15%) | Margin below healthy band | `app/ai/analysts/sales.py` | Unit economics warning |
| Funnel top SKU concentration | > 60% | Funnel breadth signal | `app/ai/analysts/funnel.py` | Narrow funnel risk |

---

## 6. Deep period insights

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| High logistics per-SKU | **25%** (0.25) | Deep insight: logistics-heavy SKU | `app/ai/deep/period_insights.py` | Aligns with `LOGISTICS_SKU_THRESHOLD` |
| High commission per-SKU | **20%** (0.20) | Deep insight: commission-heavy SKU | `app/ai/deep/period_insights.py` | WB commission pressure band |
| Low margin deep insight | < 15% | Profitable but thin margin SKU | `app/ai/deep/period_insights.py` | Margin warning |
| Cost coverage complete | ≥ 100% | Skip COGS gap bullet | `app/ai/deep/period_insights.py` | Trust gating |
| Period cause mix threshold | ≥ 25% of rev delta | Volume effect dominance | `app/ai/deep/period_causes.py` | Causal attribution |
| Period cause price effect | ≥ 35% of rev delta | Price-driven change | `app/ai/deep/period_causes.py` | Pricing signal |
| Share mix delta | ≥ 0.3 pp | SKU mix shift in causes | `app/ai/deep/period_causes.py` | Mix attribution granularity |
| Profit vs revenue gap | 2 pp | Profit lagging revenue | `app/ai/deep/period_causes.py` | Margin compression signal |

---

## 7. Executive aggregation

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Severity weight low | 10 | Prioritization score base | `app/ai/executive/aggregator.py` | Ordered severity scale |
| Severity weight medium | 25 | — | `app/ai/executive/aggregator.py` | — |
| Severity weight high | 45 | — | `app/ai/executive/aggregator.py` | — |
| Severity weight critical | 70 | — | `app/ai/executive/aggregator.py` | — |
| Top insights for narrative | 3 | Executive summary length | `app/ai/executive/aggregator.py` | Seller readability |
| Max recommendations | 15 | Final action list cap | `app/ai/executive/aggregator.py` | Prevent action overload |
| Default overall confidence | 0.5 | Empty findings fallback | `app/ai/executive/aggregator.py` | Neutral when no signals |

---

## 8. Business coverage V1

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Coverage blocks | 8 weighted | Business Coverage V1 score | `app/ai/coverage/business_coverage.py` | 50% with pilot (4/8 available) |
| Margin sub-item gate | COGS ≥ 100% | "Маржа" marked available | `app/ai/coverage/business_coverage.py` | Requires full cost coverage |
| Return rate delta bullet | ≥ 1 pp | Executive limitation trigger | `app/ai/coverage/business_coverage.py` | Material return trend |
| COGS gap limitation | < 100% | Analysis limitation text | `app/ai/coverage/business_coverage.py` | Trust transparency |

**Block weights (internal):** Sales, Marketplace costs, COGS, Promotion, External marketing, Tax, Operational, Financial, Inventory — see `assess_business_coverage()` for current weights.

---

## 9. Trust, quality gates & audit targets

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Full COGS coverage | 100% | Profit trust level FULL | `app/domain/analytics/profit_trust.py` | Authoritative margin |
| Partial COGS coverage | 80% | Profit trust PARTIAL | `app/domain/analytics/profit_trust.py` | Usable with caveat |
| Min COGS coverage | 1% | Profit trust MINIMAL | `app/domain/analytics/profit_trust.py` | Any cost data |
| Audit COGS warning | < 80% | Quality audit flag | `app/ai/quality/recommendation_audit.py` | Data quality gate |
| Audit margin warning | > 20% + "below" | False positive check | `app/ai/quality/recommendation_audit.py` | Sanity on margin claims |
| Stale context confidence cap | × 0.75–0.80 | Degraded confidence multipliers | `app/ai/quality/recommendation_quality.py` | Trust degradation |
| Phase 630B SU gate | ≥ 74.0 | Release audit pass | `scripts/phase_630_inventory_audit.py` | Baseline restoration |
| Phase 630B AI readiness gate | ≥ 86.0 | Release audit pass | `scripts/phase_630_inventory_audit.py` | Intelligence quality floor |
| Inventory insight rate gate | ≥ 25% | Release audit pass | `scripts/phase_630_inventory_audit.py` | Inventory activation proof |
| Dashboard echo gate | 0% | Release audit pass | `scripts/phase_630_inventory_audit.py` | Echo elimination |
| Actionable rate gate | 100% | Release audit pass | `scripts/phase_630_inventory_audit.py` | Seller actionability |

---

## 10. Confidence constants (analyst outputs)

| Threshold | Value | Purpose | File | Rationale |
|-----------|-------|---------|------|-----------|
| Standard high confidence | 0.88–0.92 | Domain finding confidence | Various analysts | Governed signal trust band |
| Insufficient data confidence | 0.55–0.60 | Missing data analysts | `inventory.py`, `ads.py` | Honest uncertainty |
| Low confidence analyst flag | < 0.70 | Eval suite low-confidence detection | `app/ai/evaluation/multi_layer_suite.py` | Quality monitoring |
| Analyst insufficient data base | 0.30–0.50 | Empty package handling | `app/ai/analysts/base.py` | Graceful degradation |

---

## Change control

1. Any threshold change in sections **1–3** requires `phase_630_inventory_audit.py` re-run on pilot + at least one alternate archetype (Phase 6.5.3+).
2. New thresholds must be added to this catalog in the same PR.
3. Future externalization target: `app/ai/config/thresholds.py` or env-backed registry (Phase 6.6+, not in 6.5.1 scope).

---

## Related documents

- [phase_630b_priority_calibration_report.md](phase_630b_priority_calibration_report.md)
- [inventory_priority_calibration_audit.md](inventory_priority_calibration_audit.md)
- [usefulness_framework.md](usefulness_framework.md)
- [mvp_hardening_plan.md](../release/mvp_hardening_plan.md)

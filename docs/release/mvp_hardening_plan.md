# MVP Hardening Plan — Post v0.6-mvp-intelligence

**Date:** 2026-06-07  
**Phase:** 6.5.0 (preparation)  
**Scope:** Validation and generalization only — no new business features  
**Prerequisite:** Tag `v0.6-mvp-intelligence` (milestone snapshot)

---

## 1. Purpose

Phase 6 validated Period Intelligence on a **single pilot seller** (4 WB finance reports, user `caefecb3-5789-4878-a9d4-929be573fbcc`). Metrics pass calibration gates (Seller Usefulness 80.3, AI Readiness 86.1), but **external rollout and production confidence require broader seller archetypes, datasets, and regression coverage**.

This plan defines what must be tested before promoting MVP Intelligence beyond the pilot.

---

## 2. Seller archetypes to validate

Each archetype needs: real or synthetic dataset, expected primary insight domain, expected Business Coverage score band, and pass/fail criteria.

| # | Archetype | Business shape | Primary expected insight | Coverage expectation | Priority |
|---|-----------|----------------|--------------------------|----------------------|----------|
| 1 | **Small seller** | ≤20 SKU, low revenue, minimal ads | Revenue or margin (not inventory noise) | 35–50% (missing ads/OPEX) | P0 |
| 2 | **Seasonal seller** | Sharp period delta (+/- 30%), skewed top SKUs | Revenue change / concentration | 45–55% | P0 |
| 3 | **Unprofitable seller** | Negative unit economics on top SKUs | Profit / deep period (убыточные SKU) | 50–60% (needs COGS) | P0 |
| 4 | **No-ads seller** | Zero ad spend, organic only | Ads block excluded; no false ad warnings | 40–50%, `advertising_data_coverage=false` | P0 |
| 5 | **High inventory seller** | Large frozen capital, dead stock | Inventory escalated to L1 only when critical | Inventory sub-coverage ≥66% | P0 |
| 6 | **Healthy stable seller** | Flat trends, balanced SKUs | Informational L2/L3, revenue-led primary | 50%+ | P1 |
| 7 | **High-return seller** | Returns >10%, margin erosion | Returns analyst L1 | 50–60% | P1 |
| 8 | **Logistics-heavy seller** | Logistics share >15% | Logistics analyst L1 | 50–55% | P1 |
| 9 | **Concentration risk seller** | Top-1 SKU >50% revenue | Concentration L1 | 45–55% | P1 |
| 10 | **Multi-marketplace seller** | WB + Ozon (if data available) | Marketplace comparison | TBD — not in V1 coverage | P2 |

**Pilot gap:** Current validation covers archetype **#5 partially** (inventory signals present) and **#6 partially** (stable periods). Archetypes **#1–#4, #7–#9** are **not validated** on real data.

---

## 3. Missing datasets

| Dataset | Purpose | Status | Action |
|---------|---------|--------|--------|
| Small seller WB export (≤20 SKU, 2 periods) | Threshold noise, coverage floor | Missing | Collect sanitized export or build fixture from `docs/product/fixtures/` |
| Seasonal spike period pair | Revenue change / concentration | Missing | Two consecutive periods with ±30% delta |
| Unprofitable SKU set with COGS | Profit deep insights, margin L1 | Partial (pilot has costs) | Dedicated fixture with known loss-making SKUs |
| Seller with zero ad rows | Ads exclusion logic | Missing | WB report without рекламных строк |
| High dead-stock snapshot | Inventory L1 escalation | Partial (pilot) | Snapshot with 60+ day idle, ≥3 SKU |
| Low/no inventory snapshots | `inventory_limited_signals` path | Missing | Reports only, no warehouse snapshots |
| Ozon finance export | Multi-MP coverage | Missing | Deferred to Phase 6.5+ |
| Seller without cost import | COGS gap / trust gating | Missing | Upload reports, skip costs |
| 10+ period history | Trend stability, fatigue | Missing | Longitudinal pilot extension |

**Storage location (proposed):** `tests/fixtures/seller_archetypes/` (sanitized CSV/XLSX + expected audit JSON per archetype).

---

## 4. Uncovered scenarios

### 4.1 Intelligence layer

| Scenario | Current coverage | Gap |
|----------|------------------|-----|
| Revenue drop >10% triggers L1 | Unit tests + pilot | Not tested on seasonal down-swing dataset |
| Inventory does **not** steal primary when revenue IQ higher | Phase 6.3.0B + unit tests | Only 4 pilot periods validated |
| `sales_top_sku` L1 on small catalog (1–3 SKU) | Not tested | May over-prioritize trivial leader |
| Deep period insights without inventory snapshots | Not tested | Fallback path untested on real data |
| Executive summary with 0 domain findings | Fallback in composer | No integration test on empty package |

### 4.2 Priority engine

| Scenario | Gap |
|----------|-----|
| Inventory IQ > revenue IQ + 8 pp → inventory primary | Unit-tested logic; no multi-seller replay |
| Domain-balanced lead with 5+ competing L1 domains | Not stress-tested |
| Russian text markers in deep bullets (`мёртв`, `заморож`) | Pilot-specific phrasing only |

### 4.3 Business Coverage V1

| Scenario | Gap |
|----------|-----|
| Coverage score with ads block missing | Not validated on no-ads seller |
| Coverage 50% floor with partial COGS | Single pilot mix only |
| `advertising_warning` text when spend=0 | Untested |

### 4.4 Product / UX

| Scenario | Gap |
|----------|-----|
| Seller with no AI recommendations yet | Onboarding empty state |
| Recommendation fatigue (same insight 3+ periods) | `fatigue.py` exists; no archetype replay |
| Mobile / narrow viewport recommendation detail | Not in audit scope |

### 4.5 Operations

| Scenario | Gap |
|----------|-----|
| ETL failure mid-upload → AI stale context | Trust banner path documented, not replayed |
| Rebuild during AI run | Race not validated |
| Multi-tenant RLS isolation on AI recommendations | `rls_leak_test.py` exists; not in phase audit |

---

## 5. Hardening workstreams

### WS-1 — Multi-seller audit harness (P0)

**Goal:** Remove implicit pilot default without breaking existing audits.

| Task | Detail |
|------|--------|
| Parameterize pilot UUID | Keep `PILOT_USER` as default in scripts; add `--archetype` flag mapping to fixture user IDs |
| Archetype expected metrics | JSON schema per archetype: min/max SU, AI readiness, primary domain |
| CI gate (optional) | Run audit on 3+ archetypes when DB available; skip in sandbox |

**Files:** `scripts/phase_630_inventory_audit.py`, `scripts/ai_recommendation_quality_audit.py`, new `tests/fixtures/seller_archetypes/manifest.json`

### WS-2 — Threshold externalization review (P0)

**Goal:** Document and optionally config-ize hardcoded thresholds (no logic change in v0.6).

| Constant | Location | Current | Hardening action |
|----------|----------|---------|------------------|
| `DEAD_STOCK_THRESHOLD_DAYS = 60` | `intelligence.py` | Pilot-tuned | Validate on seasonal + high-inventory archetypes |
| `SLOW_MOVER_THRESHOLD_DAYS = 30` | `intelligence.py` | Default | Same |
| `INVENTORY_RISK_ITEM_THRESHOLD = 3` | `intelligence.py` | Item count | Test small seller (≤5 SKU) |
| `FROZEN_CAPITAL_HIGH_SHARE = 20%` | `intelligence.py` | Revenue ratio | Test low-revenue seller |
| `STOCK_CONCENTRATION_HIGH = 60%` | `intelligence.py` | Capital concentration | — |
| Revenue escalation `+ 8.0` IQ points | `priority_engine.py` | Calibration constant | Sensitivity analysis on 10+ periods |
| `seller_usefulness × 0.88` | `seller_intelligence.py` | Quality dampening | Document; do not change without re-audit |
| `REVENUE_DROP_THRESHOLD = -10%` | `governed_signals.py` | Period delta | Test ±5% borderline periods |
| `LOGISTICS_HIGH_SHARE = 15%` | `governed_signals.py` | Burden share | Logistics-heavy archetype |
| `CONCENTRATION_TOP1 = 50%` | `governed_signals.py` | SKU share | Concentration archetype |

**Deliverable:** `docs/ai/threshold_catalog.md` (Phase 6.5.1, doc-only)

### WS-3 — Test suite stabilization (P0)

**Current:** 287 passed, **4 failed** (2026-06-07 run)

| Failing test | Area | Action |
|--------------|------|--------|
| `test_layer_import_rules_no_errors` | Architecture governance | Fix import violations or update rules |
| `test_six_domain_analysts_run` | Multi-layer intelligence | Align with 10-analyst package |
| `test_multi_layer_eval_suite_all_pass` | Multi-layer intelligence | Same |
| `test_ledger_builder_emits_decimal_entries` | WB parser | Parser/ledger regression |

**Gate:** `pytest tests/unit -q` green before external MVP.

### WS-4 — Documentation debt cleanup (P1)

| Task | Detail |
|------|--------|
| Remove or archive `README.v06-draft.md` | Duplicate of `README.md` post-cutover |
| Update `CHANGELOG.md` | Add v0.6 section |
| Link `real_seller_scenarios.md` from docs hub | Maps to archetypes above |
| Populate `docs/release/go_no_go/v0.6-decision.md` | Or fold into release readiness report |

### WS-5 — External MVP boundary (P1)

Per `docs/product/mvp_readiness.md`, confirm hidden surfaces before any external user:

- Ops JSON pages, raw AI runs, runtime simulation endpoints
- Financial KPI dashboard (prototype — no read APIs)
- Email recovery (now implemented — re-verify checklist)

---

## 6. Validation matrix (acceptance criteria)

Run after each archetype dataset is loaded and AI recommendations regenerated.

| Check | Target | Script |
|-------|--------|--------|
| Seller Usefulness | ≥ 74 (archetype-specific floor may apply) | `phase_630_inventory_audit.py` |
| AI Readiness | ≥ 86 (or archetype waiver documented) | same |
| Dashboard Echo | 0% | same |
| Actionable Rate | 100% | same |
| Inventory Insight Rate | ≥ 25% when snapshots exist; 0% acceptable when none | same |
| Primary domain | Matches archetype expectation | Manual + JSON assertion |
| Business Coverage | Documented band | `business_coverage.py` output |
| No pilot UUID in production config | — | Code review |

---

## 7. Recommended phase sequence

```text
6.5.0  Release audit + this plan                    ← current
6.5.1  Threshold catalog + test fixes + README draft cleanup
6.5.2  Archetype fixtures (P0 sellers #1–#5)
6.5.3  Multi-seller audit replay + metrics report
6.6.0  External MVP soft launch (if all P0 archetypes pass)
```

---

## 8. Out of scope (explicit)

- Operating Director production activation
- Ads / Tax / OPEX coverage expansion (Phase 6.3 blueprint)
- LLM prompt changes
- New domain analysts
- API breaking changes

---

## 9. Success definition

MVP Hardening is **complete** when:

1. All **P0 archetypes** (#1–#5) pass validation matrix on dedicated datasets
2. Unit test suite is **100% green**
3. Audit scripts run against **≥3 distinct user fixtures** without manual pilot UUID
4. Threshold catalog published and signed off
5. Release readiness report updated with **GO for external MVP**

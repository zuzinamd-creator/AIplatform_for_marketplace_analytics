# Multi-Seller Replay Report — Phase 6.5.3

**Date:** 2026-06-07  
**Phase:** 6.5.3 — Multi-Seller Replay & Validation  
**Consolidated data:** [reports/multi_seller_replay.json](../../reports/multi_seller_replay.json)  
**Discovery snapshot:** [reports/multi_seller_discovery.json](../../reports/multi_seller_discovery.json)

**Critical rule honored:** No changes to production AI, thresholds, Priority Engine, Inventory Intelligence, or usefulness calculations.

---

## Summary

| Metric | Value |
|--------|-------|
| Sellers discovered in database | **2** |
| Sellers with AI recommendations | **1** |
| Total finance reports (all sellers) | **5** |
| Archetypes evaluated (replay) | **1 / 5** |
| Archetypes PASS | **1** |
| Archetypes FAIL | **0** |
| Archetypes SKIP (GAP) | **4** |
| Pass rate (evaluated only) | **100%** (1/1) |

### Release decision

| Tag | Decision |
|-----|----------|
| **`v0.6-mvp-intelligence`** | **NO-GO** |

**Rationale:** GO criteria require ≥5 sellers and ≥4/5 archetypes PASS. Only 1 archetype could be replayed on real data. No AI regression detected on pilot; generalization **not proven**.

---

## Task 1 — Dataset discovery

### Seller inventory (production database)

| seller_id | email | SKU | Finance reports | AI recs | Period | Revenue (₽) | Profit (₽) | Inv snapshots | Rev Δ% | Inferred tags |
|-----------|-------|-----|-----------------|---------|--------|-------------|--------------|---------------|--------|---------------|
| `caefecb3-5789-4878-a9d4-929be573fbcc` | margarita.zuzina@mail.ru | 48 | 4 | 4 | 2026-03-12 → 2026-05-31 | 1,496,677 | 651,112 | 2,353 | +18.2% | high_inventory |
| `1267cd81-ca57-4773-8f5c-0febe84488f4` | upload-test@example.com | 42 | 1 | **0** | 2026-03-10 → 2026-05-24 | 2,982,663 | 2,451,617 | 4,003 | **−23.1%** | high_inventory |

**Notes:**

- Only **2 tenants** have processed finance data in the database.
- Second seller has ETL aggregates and inventory snapshots but **no AI recommendations** (cannot replay audits).
- No seller has ≤20 SKU (smallest catalog: 42 SKU).
- No seller has negative period profit.
- No ad-spend signal available at discovery layer to classify `no_ads_seller`.

---

## Task 2 — Archetype mapping

| Archetype | Mapped seller | Status | Source |
|-----------|---------------|--------|--------|
| `small_seller` | — | **GAP** | No seller ≤20 SKU |
| `seasonal_seller` | — | **GAP** | No seller with AI recs + \|Δrev\| ≥25%; partial candidate below |
| `unprofitable_seller` | — | **GAP** | All sellers profitable (net_profit > 0) |
| `no_ads_seller` | — | **GAP** | Cannot confirm zero ad spend from DB discovery |
| `high_inventory_seller` | `caefecb3-…` (pilot) | **MAPPED** | manifest + validated |

### Partial candidate (not replayable)

| Seller | Potential archetype | Blocker |
|--------|---------------------|---------|
| `1267cd81-…` (upload-test) | `seasonal_seller` (−23.1% rev delta, near ±25% threshold) | 0 AI recommendations; 1 finance report only |

**No artificial data created.** Mapping uses real project tenants only.

---

## Task 3 — Replay execution

Replay method: read-only audit (no migrate/reset). Four audit paths consolidated via `scripts/multi_seller_replay.py`:

| Archetype | Runner | phase_630 | phase_622 | quality_audit | Result |
|-----------|--------|-----------|-----------|---------------|--------|
| small_seller | SKIP | — | — | — | GAP |
| seasonal_seller | SKIP | — | — | — | GAP |
| unprofitable_seller | SKIP | — | — | — | GAP |
| no_ads_seller | SKIP | — | — | — | GAP |
| high_inventory_seller | ✅ | ✅ | ✅ | ✅ | **PASS** |

Command executed:

```bash
.venv/bin/python scripts/multi_seller_replay.py --json-out reports/multi_seller_replay.json
```

---

## Task 4 — PASS / FAIL evaluation

### high_inventory_seller — **PASS**

| Metric | Value | Band min | Band target | Status |
|--------|-------|----------|-------------|--------|
| Seller Usefulness | **80.3** | 74.0 | 80.0 | TARGET |
| AI Readiness | **86.1** | 86.0 | 86.0 | TARGET |
| Actionable Rate | **100%** | 100% | 100% | STRETCH |
| Inventory Insight Rate | **100%** | 50% | 100% | STRETCH |
| Dashboard Echo | **0%** | max 0% | 0% | STRETCH |

**Insight validation:** PASS  
- Expected hits: `inventory_frozen_capital`, `inventory_stock_concentration`, `inventory_risk_high`  
- Optional: `sales_top_sku`  
- Primary domain: `revenue` (revenue protection active)  
- Forbidden: none hit  

### Skipped archetypes (GAP — not FAIL)

| Archetype | Status | Reason |
|-----------|--------|--------|
| small_seller | SKIP | No matching seller in DB |
| seasonal_seller | SKIP | No matching seller with AI recs |
| unprofitable_seller | SKIP | No loss-making seller |
| no_ads_seller | SKIP | No classifiable zero-ads seller |

**Important:** SKIP due to **data GAP** is not an AI FAIL. No archetype failed metric bands on replay.

---

## Task 5 — Metric stability vs pilot

| Metric | Pilot (6.3.0B) | Replay (6.5.3) | Delta | Stable? |
|--------|----------------|----------------|-------|---------|
| Seller Usefulness | 80.3 | 80.3 | 0.0 | ✅ |
| AI Readiness | 86.1 | 86.1 | 0.0 | ✅ |
| Actionable Rate | 100% | 100% | 0% | ✅ |
| Inventory Insight Rate | 100% | 100% | 0% | ✅ |
| Dashboard Echo | 0% | 0% | 0% | ✅ |
| Insight Quality | — | 91.2 | — | ✅ |
| Inventory Sub-Coverage | 75% | 75% | 0% | ✅ |

**Conclusion:** Metrics on pilot/high_inventory archetype are **bit-stable** — no regression detected.

### Metric distributions (evaluated archetypes only)

| Metric | Min | Max | Avg | n |
|--------|-----|-----|-----|---|
| Seller Usefulness | 80.3 | 80.3 | 80.3 | 1 |
| AI Readiness | 86.1 | 86.1 | 86.1 | 1 |
| Dashboard Echo | 0% | 0% | 0% | 1 |

---

## Task 6 — Failure analysis

### No FAIL archetypes

Zero archetypes failed metric bands. No production fixes required or applied.

### GAP analysis (4 skipped archetypes)

| Archetype | Root cause | Affected module | Threshold involvement | Business impact |
|-----------|------------|-----------------|----------------------|-----------------|
| **small_seller** | No tenant ≤20 SKU in DB | Data / onboarding | `INVENTORY_RISK_ITEM_THRESHOLD=3` untested on tiny catalogs | Unknown primary-selection behavior for ≤20 SKU |
| **seasonal_seller** | No tenant with AI recs + material period delta | Data pipeline | `REVENUE_DROP/GROWTH ±10%` untested on real swing | Revenue change analyst unvalidated on live seasonal data |
| **unprofitable_seller** | All tenants profitable | Data | Deep period «убыточные SKU» path untested | Profit-led primary unconfirmed on loss-making business |
| **no_ads_seller** | No ad-spend classification in discovery; all tenants ambiguous | Data + Coverage V1 | `ads_no_governed_spend` untested in isolation | Risk of false ad recommendations unquantified |

### Secondary data gap

| Seller | Issue | Impact |
|--------|-------|--------|
| upload-test@example.com | 1 report, 0 AI recs, high inventory data | Cannot extend replay to second tenant |

---

## Task 7 — Risk assessment

### Technical risk — **Medium**

- AI pipeline stable on pilot (metrics unchanged).
- Architecture supports multi-tenant replay (`--archetype`, `multi_seller_replay.py`).
- Only 1/5 replay paths exercised on real recommendations.

### Product risk — **High**

- External MVP would serve seller types **never validated** (small, seasonal, unprofitable, no-ads).
- Business Coverage 50% normalized on single seller shape.

### AI risk — **Medium-High**

- Priority Engine +8 pp revenue protection validated on **one** IQ distribution only.
- Inventory escalation rules validated on **one** inventory profile.
- No evidence of regression, but **no evidence of generalization**.

---

## GO criteria checklist

| Criterion | Required | Actual | Met? |
|-----------|----------|--------|------|
| Sellers | ≥ 5 | **2** (1 replayable) | ❌ |
| Archetypes PASS | ≥ 4/5 | **1/5** | ❌ |
| Seller Usefulness ≥ 75 (majority) | majority | 1/1 = 100% | ✅* |
| AI Readiness ≥ 80 (majority) | majority | 1/1 = 100% | ✅* |
| Dashboard Echo ≤ 5% | all | 0% | ✅ |
| Critical AI regressions | none | none on pilot | ✅ |

\*Majority trivially satisfied with n=1 — not statistically meaningful.

---

## Recommendation

### **NO-GO** for release tag `v0.6-mvp-intelligence`

**What NO-GO means here:**

- **Not** a rejection of Phase 6 engineering work — pilot metrics stable, all quality gates pass on known data.
- **Is** a rejection of **generalization claims** required for MVP release sign-off.
- Tag may still be created as **internal milestone** with documented scope limitation (1 seller, 1 archetype).

### Recommended next steps (Phase 6.5.4 or 6.6 prep)

1. **Onboard 4+ real sellers** matching P0 archetypes (or upload historical exports to dedicated test tenants).
2. Run `backfill_ai_recommendations.py` for each new tenant.
3. Re-run `scripts/multi_seller_replay.py` until ≥4/5 PASS.
4. Assign `user_id` in manifest for validated archetypes.
5. Re-evaluate GO for `v0.6-mvp-intelligence` or proceed to `v0.6.1-generalization` tag.

### Conditional milestone tag (optional, human decision)

If product accepts **pilot-only validation scope**:

- Tag `v0.6-mvp-intelligence` as **milestone** with release notes stating: *validated on 1 seller, 4 reports, high_inventory archetype only*.
- External MVP remains blocked until multi-seller replay passes.

---

## Artifacts

| Artifact | Path |
|----------|------|
| Consolidated replay JSON | `reports/multi_seller_replay.json` |
| Discovery JSON | `reports/multi_seller_discovery.json` |
| Replay orchestrator | `scripts/multi_seller_replay.py` |
| Archetype manifest | `tests/fixtures/seller_archetypes/manifest.json` |
| Framework docs | `docs/testing/archetype_validation_framework.md` |

---

## Related documents

- [phase_652_archetype_framework_report.md](phase_652_archetype_framework_report.md)
- [archetype_validation_readiness.md](archetype_validation_readiness.md)
- [v0.6_release_readiness_report.md](v0.6_release_readiness_report.md)
- [threshold_catalog.md](../ai/threshold_catalog.md)

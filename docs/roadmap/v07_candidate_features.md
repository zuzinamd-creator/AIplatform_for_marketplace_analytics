# v0.7 Candidate Features — Roadmap Draft

**Date:** 2026-06-07  
**Phase:** 6.6.0 (planning only — no implementation)  
**Baseline:** `v0.6-pilot-validated` — Period Intelligence MVP, pilot seller validated  
**Principle:** Maximize value for current pilot client first; expand generalization when second client appears

---

## Priority framework

| Tier | Meaning | Horizon |
|------|---------|---------|
| **P0** | Unblocks pilot client daily decisions | v0.7.0 |
| **P1** | High seller value; builds on v0.6 AI | v0.7.x |
| **P2** | Generalization & scale | v0.8+ |
| **Research** | Architecture exploration | backlog |

---

## 1. Advertising Intelligence

**Tier:** P1  
**Phase 6.3 blueprint:** Ads block in Business Coverage (currently OFF)

### Problem

Pilot seller has no governed ad-spend KPIs. Coverage V1 = 50%. AI cannot assess ad ROI, campaign efficiency, or promotion impact.

### Candidate scope

- Governed ad-spend signals from WB promotion reports
- `ads_analyst` upgrade from context-only to L1-capable findings
- Business Coverage block activation (promotion + external marketing)
- `advertising_data_coverage=true` path validation

### Dependencies

- WB ads report ETL (or finance report ad rows parsing)
- Archetype `no_ads_seller` vs `ads_active_seller` validation
- Threshold catalog extension (CPM, ACOS bands)

### Effort estimate

**L** (3–4 weeks) — data model + analyst + coverage + audit

### Success metrics

- Business Coverage ≥ 62% on pilot
- No false ad recommendations when spend = 0
- `no_ads_seller` archetype PASS on replay

---

## 2. Forecasting

**Tier:** P2  
**Type:** New intelligence domain

### Problem

Period Intelligence is **retrospective**. Sellers ask «what will happen next month?» — not covered.

### Candidate scope

- Simple statistical forecasts: revenue, units, margin (30/60/90 day)
- Seasonal decomposition for `seasonal_seller` archetype
- Forecast confidence bands in executive summary
- **Advisory-only** — no automated actions

### Dependencies

- ≥6 periods history per seller (pilot has 4 — thin)
- Time-series store or aggregate extension
- New `forecast_analyst` or deep layer extension

### Effort estimate

**L–XL** (4–6 weeks)

### Risks

- Thin data on pilot (4 reports) → low forecast confidence
- Must not contaminate deterministic MVP with unvalidated ML

---

## 3. SKU Prioritization

**Tier:** P0–P1  
**Type:** Product + AI enhancement

### Problem

Sellers with 48+ SKU need «what to fix first today» — beyond single primary insight.

### Candidate scope

- **Today's Focus** queue: top 3–5 SKU actions ranked by impact × urgency
- Integration with existing `prioritization.py`, `fatigue.py`
- Dashboard widget: prioritized SKU list with drill-down
- Deterministic ranking (revenue at risk, margin leak, inventory frozen capital)

### Dependencies

- SKU-level governed metrics (partially available)
- Frontend SKU explorer (Tier 2 in refined roadmap)

### Effort estimate

**M** (2–3 weeks)

### Success metrics

- Seller completes weekly review in <10 min (product validation goal)
- Usefulness maintained ≥ 74 on pilot

---

## 4. Executive Summary 2.0

**Tier:** P1  
**Type:** Evolution of existing v2

### Problem

Executive Summary v2 works but is text-heavy; cross-domain narrative could be richer without LLM dependency.

### Candidate scope

- Structured executive blocks: **Situation → Impact → Action** (deterministic templates)
- Cross-report reasoning: compare last 2 periods in one narrative
- Plain-language severity badges (critical / watch / ok)
- Mobile-friendly summary layout

### Note

«Executive Summary 2.0» here means **UX/narrative vNext**, not replacing existing `executive/aggregator.py` logic without audit.

### Dependencies

- Multi-period recommendation history
- Insight quality scores per block

### Effort estimate

**M** (2 weeks backend + 1 week frontend)

---

## 5. Cross-report reasoning

**Tier:** P1  
**Type:** Intelligence layer extension

### Problem

Each recommendation is period-scoped. Sellers upload reports sequentially — AI does not explicitly chain «report N vs report N-1» across upload events.

### Candidate scope

- **Period chain memory:** link consecutive AI runs for same seller
- Detect trends across uploads: «third consecutive inventory warning»
- Fatigue integration: suppress repeat insights unless severity increased
- `strategic_memory` store activation (scaffold exists)

### Dependencies

- `app/ai/memory/strategic.py` production wiring
- Backfill history for pilot (4 periods available)

### Effort estimate

**M–L** (3 weeks)

### Success metrics

- Reduced recommendation fatigue scores
- Trend findings in executive lead

---

## 6. Automated anomaly detection

**Tier:** P1–P2  
**Type:** Analyst enhancement

### Problem

`anomaly_analyst` currently often returns `anomaly_none`. Deeper statistical anomaly detection could catch ETL drift, payout mismatches, sudden KPI breaks.

### Candidate scope

- Governed anomaly rules: payout mismatch, cost coverage drop, revenue spike/drop without SKU driver
- Integration with ops trust banners (`TrustBanners`)
- Plain-language anomaly table in seller UI (refined roadmap #8)
- Queue-triggered re-analysis on anomaly flag

### Dependencies

- `snapshot_consistency_checks`, drift probes (ops layer exists)
- Anomaly → AI context pipeline

### Effort estimate

**M** (2–3 weeks)

---

## 7. Additional v0.7 candidates (from product roadmap)

| Feature | Tier | Seller value | Notes |
|---------|------|--------------|-------|
| Weekly Analysis page | P0 | Period compare, ABC, inventory-risk | Wire existing APIs |
| Dashboard period selector | P0 | 7d/14d/30d views | Small frontend |
| SKU mapping CRUD | P0 | Profitability accuracy | Blocks margin trust |
| Server-side tenant settings | P1 | Cross-device prefs | LocalStorage today |
| Email notifications | P1 | Upload status | SMTP exists |
| Tax / OPEX coverage blocks | P2 | Coverage 50% → 75%+ | Phase 6.3 blueprint |
| Conversion / funnel KPIs | P2 | Card funnel vs Funnel analyst | Data gap |
| Multi-marketplace (Ozon) | P2 | Second MP | ETL placeholder |

---

## Suggested v0.7 sequence

```text
v0.7.0  SKU Prioritization + Weekly Analysis (pilot client value)
v0.7.1  Advertising Intelligence (coverage expansion)
v0.7.2  Cross-report reasoning + Executive Summary 2.0 UX
v0.7.3  Automated anomaly detection (seller-facing)
v0.8.0  Forecasting + second-client archetype onboarding
```

---

## Explicit non-goals for v0.7 planning

- Operating Director production activation (without separate ADR)
- Threshold recalibration without audit replay
- External MVP launch (unless explicitly replanned)
- LLM-first intelligence replacement

---

## Related documents

- [refined_roadmap.md](../product/refined_roadmap.md)
- [phase_63_architecture_blueprint.md](../ai/phase_63_architecture_blueprint.md)
- [v06_release_manifest.md](../release/v06_release_manifest.md)
- [technical_debt_register.md](../release/technical_debt_register.md)

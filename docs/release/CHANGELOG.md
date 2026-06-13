# Changelog — v0.6 MVP Intelligence

All notable changes for the Period Intelligence MVP release line.  
Root project changelog: [../../CHANGELOG.md](../../CHANGELOG.md) (Phase 5 and earlier).

---

## [6.5.1] — 2026-06-07 — Release Fix Pack & Threshold Catalog

### Fixed
- **Test stabilization:** 4 failing unit tests resolved (287 → 291 pass, 100%)
- Architecture governance allowlist extended for `intelligence.py` and `period_queries.py`
- Multi-layer eval suite updated for 10 domain analysts
- Ledger builder test fixture aligned with WB row semantics (`operation_type` required for SALE)

### Added
- `docs/ai/threshold_catalog.md` — centralized threshold registry
- `docs/release/test_stabilization_report.md`
- `docs/release/hardening_readiness.md`

### Removed
- `README.v06-draft.md` from root → archived as `docs/archive/README_v06_draft.md`

---

## [6.5.0] — 2026-06-07 — Release Audit

### Added
- `docs/release/v0.6_release_readiness_report.md` — readiness score 74/100
- `docs/release/mvp_hardening_plan.md` — P0 seller archetypes and workstreams

### Decision
- **GO** for milestone tag `v0.6-mvp-intelligence`
- **NO-GO** for external MVP rollout (single pilot, missing archetype validation)

---

## [6.4.2] — 2026-06-07 — README Cutover

### Changed
- `README.md` replaced with v0.6 product README (491 lines)
- Blockers fixed: self-reference §19, license, roadmap numbering, Windows anchor

### Added
- `docs/README.md` — documentation hub
- `docs/archive/README_pre_v06.md` — pre-v0.6 snapshot (2923 lines)
- `docs/release/v0.6-mvp-intelligence.md` — release notes
- `docs/operations/environment_variables.md`

### Decision
- **CUTOVER GO** ([readme_cutover_report.md](readme_cutover_report.md))

---

## [6.4.1] — 2026-06-07 — Documentation Review

### Added
- README cutover plan and blocker analysis
- Release folder structure (`docs/release/`, `docs/archive/`)

### Notes
- Identified 5 blockers before cutover (all resolved in 6.4.2)

---

## [6.3.0B] — 2026-06-07 — Priority Calibration

### Fixed
- Inventory L1 over-prioritization causing Seller Usefulness drop (74.1 → 68.2)
- Revenue insight (`sales_top_sku`) restored as eligible primary

### Changed
- **Revenue Protection Layer** in `priority_engine.py` — inventory primary only if IQ > revenue + 8 pp
- **Inventory Escalation Rules** — L1 only for critical dead stock / high frozen capital
- **Executive rebalancing** — domain-balanced lead, max 1 inventory slot
- **Inventory deduplication** — semantic buckets (dead/slow/frozen/concentration/risk)

### Results (pilot audit)
- Seller Usefulness **80.3** (≥ 74 ✅)
- AI Readiness **86.1** (≥ 86 ✅)
- Inventory Insight Rate **100%** preserved

---

## [6.3.0] — 2026-06-07 — Inventory Intelligence

### Added
- `app/domain/inventory/intelligence.py` — dead stock, slow movers, frozen capital, concentration, risk
- `InventoryAnalyst` — 5 insight types with Russian statements
- `scripts/phase_630_inventory_audit.py` — quality gate with before/after delta

### Changed
- Inventory wired into governed signals, executive aggregator, deep period insights

### Results (pilot audit)
- Inventory Insight Rate 0% → **100%**
- Inventory Sub-Coverage 25% → **75%**
- Side effect: temporary SU drop → fixed in 6.3.0B

---

## [6.2.2] — 2026-06-06 — Intelligence Stabilization

### Added
- **Business Coverage V1** — 8-block weighted coverage model
- **Executive Summary v2** persisted in recommendations
- Root cause confidence, analysis limitations, advertising warning
- `lineage.insight_engine_version: coverage_v1`
- Migration audit (`phase_621_migration_audit.py`) + backfill scripts

### Results (pilot)
- Business Coverage **50%** (4/8 blocks with pilot data)
- Dashboard Echo **0%**
- Actionable Rate **100%**

---

## [6.2.1] — 2026-06-06 — Echo Elimination

### Added
- 10 domain analysts wired through governed signals
- Insight Priority Engine with L1/L2/L3 classification
- Recommendation quality audit: Insight / Dashboard Echo / False Positive / Data Quality
- Deep period insights (unprofitable SKUs, high logistics/commission)
- GO/NO-GO quality gates in audit scripts (`phase_622_insight_audit.py`)

### Fixed
- Dashboard Echo eliminated (KPI restatement removed from primary titles)
- Deterministic insight-driven titles and summaries

### Results (pilot)
- Seller Usefulness **74.1**
- AI Readiness **85.7**
- Dashboard Echo **0%**

---

## Metrics reference (pilot baseline)

Source: `reports/phase_630_inventory_audit.json` — user `caefecb3-5789-4878-a9d4-929be573fbcc`, 4 WB reports.

| Metric | 6.2.1 | 6.3.0 (pre-cal) | 6.3.0B |
|--------|-------|-----------------|--------|
| Seller Usefulness | 74.1 | 68.2 | **80.3** |
| AI Readiness | 85.7 | 85.3 | **86.1** |
| Dashboard Echo | 0% | 0% | 0% |
| Inventory Insight Rate | 0% | 100% | 100% |

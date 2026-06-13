# v0.6 Release Manifest — `v0.6-pilot-validated`

**Codename:** Pilot Validated Intelligence  
**Target tag:** `v0.6-pilot-validated`  
**Date:** 2026-06-07  
**Scope:** Single pilot seller (WB finance, 4 reports) — **not** external multi-tenant MVP

---

## 1. Release composition

### Core platform (unchanged baseline)

| Layer | Path | Role |
|-------|------|------|
| Backend API | `app/api/` | FastAPI routes, tenant isolation |
| Services | `app/services/` | Business orchestration |
| ETL | `app/etl/` | Report ingest, worker, rebuild |
| Domain | `app/domain/` | Ledger, inventory intelligence, reports |
| Frontend | `frontend/src/` | Seller dashboard, AI UX |
| Migrations | `alembic/versions/` | PostgreSQL schema |

### AI intelligence (Phase 6 deliverables)

| Component | Path | Phase |
|-----------|------|-------|
| Domain analysts (×10) | `app/ai/analysts/` | 6.2.1 |
| Insight Priority Engine | `app/ai/insights/priority_engine.py` | 6.2.1, 6.3.0B |
| Business Coverage V1 | `app/ai/coverage/business_coverage.py` | 6.2.2 |
| Executive aggregator | `app/ai/executive/aggregator.py` | 6.2.2 |
| Inventory Intelligence | `app/domain/inventory/intelligence.py` | 6.3.0 |
| Inventory Analyst | `app/ai/analysts/inventory.py` | 6.3.0 |
| Seller usefulness | `app/ai/product/seller_intelligence.py` | 6.2.x |
| Deep period insights | `app/ai/deep/` | 6.2.1 |

### Validation & release infrastructure

| Artifact | Path |
|----------|------|
| Threshold catalog | `docs/ai/threshold_catalog.md` |
| Archetype manifest | `tests/fixtures/seller_archetypes/manifest.json` |
| Archetype validation | `scripts/archetype_validation.py` |
| Multi-seller replay | `scripts/multi_seller_replay.py` |
| Phase audit scripts | `scripts/phase_630_inventory_audit.py`, etc. |

### Documentation bundle

| Document | Purpose |
|----------|---------|
| `README.md` | v0.6 product README |
| `docs/README.md` | Documentation hub |
| `docs/release/CHANGELOG.md` | Phase 6 changelog |
| `docs/release/v06_release_manifest.md` | This manifest |
| `docs/testing/archetype_validation_framework.md` | Validation methodology |

---

## 2. Completed phases

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 6.2.1 | Echo elimination, 10 domain analysts, quality audit | ✅ |
| 6.2.2 | Business Coverage V1, Executive Summary v2 | ✅ |
| 6.3.0 | Inventory Intelligence activation | ✅ |
| 6.3.0B | Priority calibration (revenue protection) | ✅ |
| 6.3 | Architecture blueprint (Ads, Tax, OPEX roadmap) | ✅ doc |
| 6.4.1 | Documentation review | ✅ |
| 6.4.2 | README cutover | ✅ CUTOVER GO |
| 6.5.0 | Release audit | ✅ |
| 6.5.1 | Test stabilization (299/299), threshold catalog | ✅ |
| 6.5.2 | Archetype Validation Framework | ✅ |
| 6.5.3 | Multi-seller replay (pilot PASS, 4 GAPs) | ✅ documented |
| 6.6.0 | Release preparation (this manifest) | ✅ |

---

## 3. Key capabilities at release

### Period Intelligence MVP

- Deterministic domain analysts over governed KPI snapshots
- Insight-driven titles and summaries (Dashboard Echo 0%)
- Business Coverage V1 with advertising warning and analysis limitations
- Executive summary v2 persisted in recommendations

### Inventory Intelligence

- Dead stock, slow movers, frozen capital, concentration, risk level
- Inventory wired into analysts, executive layer, deep insights
- Priority calibration: revenue-led primary unless inventory critically escalated (+8 pp IQ rule)

### Seller-facing quality

- Seller Usefulness scoring with actionable payloads
- Recommendation workflow states (active, snoozed, dismissed, etc.)
- Russian UI copy for WB seller context

### Operations

- RLS tenant isolation
- ETL queue with retry and dead-letter
- Protected production user guard in tests

---

## 4. Pilot validation metrics

Source: `reports/phase_630_inventory_audit.json`, replay `reports/multi_seller_replay.json`

| Metric | Value | Gate |
|--------|-------|------|
| Seller Usefulness | **80.3** | ≥ 74 ✅ |
| AI Readiness | **86.1** | ≥ 86 ✅ |
| Actionable Rate | **100%** | 100% ✅ |
| Inventory Insight Rate | **100%** | ≥ 25% ✅ |
| Dashboard Echo | **0%** | 0% ✅ |
| Business Coverage V1 | 50% | pilot-limited ⚠️ |
| Unit tests | **299/299** | pass ✅ |

**Pilot user:** `caefecb3-5789-4878-a9d4-929be573fbcc` — 4 WB finance reports, 48 SKU.

---

## 5. Known limitations

### Explicitly in scope limitation

This release validates AI on **one pilot seller** only. Multi-archetype generalization (small, seasonal, unprofitable, no-ads) is **not claimed**.

### Product limitations

| Limitation | Impact |
|------------|--------|
| Manual report upload only | No live WB/Ozon API sync |
| Business Coverage 50% | Ads, Tax, OPEX, Conversion blocks off |
| Ozon ETL placeholder | WB-first |
| Financial KPI dashboard prototype | Limited read APIs for full analytics MVP |
| Operating Director scaffold | Not production |
| Explainability JSON-heavy | UX friction for non-technical sellers |

### Data limitations

| Limitation | Impact |
|------------|--------|
| 2 tenants in DB, 1 with AI recs | Multi-seller replay 1/5 archetypes |
| Thresholds not externalized to config | Change requires code + re-audit |
| Thresholds calibrated on pilot IQ distribution | Sensitivity on other sellers unknown |

---

## 6. Current risks

| Risk | Severity | Mitigation path |
|------|----------|-----------------|
| Single-seller validation | Medium (accepted for pilot tag) | Archetype onboarding when needed |
| Hardcoded thresholds | Medium | `threshold_catalog.md`; config in v0.7+ |
| 50% Business Coverage perceived as complete | Low | Document in UI/release notes |
| Root `CHANGELOG.md` stale (Phase 5 only) | Low | Sync or redirect to `docs/release/CHANGELOG.md` |
| ~130 docs outside hub index | Low | Incremental hub updates |
| External MVP blocked | N/A | Not a goal for this tag |

---

## 7. Tag naming

| Tag | Meaning | Status |
|-----|---------|--------|
| `v0.6-mvp-intelligence` | Original milestone name (README cutover) | Superseded by scoped tag |
| **`v0.6-pilot-validated`** | **This release** — pilot metrics stable, 0 AI regression | **Recommended** |

---

## Related documents

- [v06_release_readiness.md](v06_release_readiness.md)
- [technical_debt_register.md](technical_debt_register.md)
- [multi_seller_replay_report.md](multi_seller_replay_report.md)
- [CHANGELOG.md](CHANGELOG.md)

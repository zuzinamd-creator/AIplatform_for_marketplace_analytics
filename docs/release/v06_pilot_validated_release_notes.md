# v0.6-pilot-validated — Release Notes

**Milestone:** `v0.6-pilot-validated`  
**Codename:** Pilot Validated Intelligence  
**Date:** 2026-06-13  
**Decision:** GO  
**Release Readiness:** 88 / 100  
**External MVP:** NO-GO (not a goal for this tag)

---

## Summary

This milestone freezes the Period Intelligence MVP after a full Phase 6 delivery cycle. The platform now provides governed, deterministic AI recommendations for a validated pilot seller on Wildberries finance data.

Completed work spans Inventory Intelligence, Priority Engine calibration, documentation cutover, release audit, test stabilization, archetype validation framework, multi-seller replay, and release preparation.

**Phases included:**

| Phase | Deliverable |
|-------|-------------|
| 6.2.1 | Echo elimination, 10 domain analysts, quality audit |
| 6.2.2 | Business Coverage V1, Executive Summary v2 |
| 6.3.0 | Inventory Intelligence activation |
| 6.3.0B | Priority calibration (revenue protection) |
| 6.4.1 | Documentation review |
| 6.4.2 | README cutover |
| 6.5.0 | Release audit |
| 6.5.1 | Test stabilization, threshold catalog |
| 6.5.2 | Archetype Validation Framework |
| 6.5.3 | Multi-seller replay |
| 6.6.0 | Release preparation |
| 6.6.1 | Milestone freeze (this release) |

---

## Key Capabilities

### Period Intelligence MVP

- Deterministic domain analysts over governed KPI snapshots
- Insight-driven titles and summaries (Dashboard Echo 0%)
- Business Coverage V1 with advertising warning and analysis limitations
- Executive summary v2 persisted in recommendations
- Period picker, compare mode, and deep SKU insights

### Inventory Intelligence

- Dead stock, slow movers, frozen capital, concentration, risk level
- Inventory wired into analysts, executive layer, and deep insights
- Priority calibration: revenue-led primary unless inventory critically escalated

### Seller-facing quality

- Seller Usefulness scoring with actionable payloads
- Recommendation workflow states (active, snoozed, dismissed, etc.)
- Russian UI copy for WB seller context

### Operations & security

- RLS tenant isolation
- ETL queue with retry and dead-letter
- Protected production user guard in tests
- Architecture governance check and audit script suite

---

## AI Capabilities

| Capability | Description |
|------------|-------------|
| **10 domain analysts** | Revenue, inventory, concentration, logistics, returns, and governed signals |
| **Insight Priority Engine** | Calibrated ranking with revenue protection and inventory escalation |
| **Inventory Intelligence** | Dead stock, slow movers, frozen capital, concentration analysis |
| **Business Coverage V1** | Partial coverage (50%) with explicit limitation warnings |
| **Executive aggregator** | Cross-domain summary with persisted recommendation payloads |
| **Deep period insights** | Period-over-period causal analysis and SKU-level drill-down |
| **Seller usefulness scoring** | Actionable rate, echo detection, quality audit pipeline |
| **Archetype validation** | Manifest-driven replay framework for seller archetypes |
| **Threshold catalog** | ~70 documented constants for audit and calibration |

---

## Validation Results

Source: `reports/phase_630_inventory_audit.json`, `reports/multi_seller_replay.json`

| Metric | Value | Gate |
|--------|-------|------|
| Seller Usefulness | **80.3** | ≥ 74 ✅ |
| AI Readiness | **86.1** | ≥ 86 ✅ |
| Actionable Rate | **100%** | 100% ✅ |
| Inventory Insight Rate | **100%** | ≥ 25% ✅ |
| Dashboard Echo | **0%** | 0% ✅ |
| Business Coverage V1 | 50% | pilot-limited ⚠️ |
| Unit tests | **299/299** | pass ✅ |
| Release readiness | **88/100** | ≥ 85 ✅ |
| AI regression on replay | **0** | pass ✅ |

**Pilot user:** `caefecb3-5789-4878-a9d4-929be573fbcc` — 4 WB finance reports, 48 SKU.

---

## Known Limitations

### Single seller validation

This release validates AI on **one pilot seller** only. Multi-archetype generalization (small, seasonal, unprofitable, no-ads) is documented but **not claimed**. Multi-seller replay found 4 archetype GAPs — acceptable for pilot scope.

### Coverage limitations

- Business Coverage V1 = **50%** — Ads, Tax, OPEX, and Conversion blocks are off
- Operating Director scaffold exists but is not production-integrated
- Explainability remains JSON-heavy for non-technical sellers

### Data gaps

- Manual report upload only — no live WB/Ozon API sync
- Ozon ETL is a placeholder (WB-first)
- Thresholds are hardcoded (~70 constants) — not externalized to config
- Thresholds calibrated on pilot IQ distribution — sensitivity on other sellers unknown
- 2 tenants in DB, 1 with AI recommendations

### External MVP

External multi-tenant MVP launch is **explicitly out of scope** for this tag.

---

## Next Milestone

**v0.7** — see [v07_candidate_features.md](../roadmap/v07_candidate_features.md)

Priority candidates:

1. SKU Prioritization + Weekly Analysis (pilot daily value)
2. Advertising Intelligence (Business Coverage expansion)
3. Cross-report reasoning + Executive Summary 2.0 UX
4. Automated anomaly detection
5. Forecasting (v0.8 horizon)

---

## Related documents

- [v06_release_manifest.md](v06_release_manifest.md)
- [v06_release_readiness.md](v06_release_readiness.md)
- [technical_debt_register.md](technical_debt_register.md)
- [phase_660_release_preparation_report.md](phase_660_release_preparation_report.md)
- [multi_seller_replay_report.md](multi_seller_replay_report.md)

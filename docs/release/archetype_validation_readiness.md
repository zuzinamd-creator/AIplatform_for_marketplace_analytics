# Archetype Validation Readiness — Phase 6.5.2

**Date:** 2026-06-07  
**Framework version:** 1.0  
**Manifest:** `tests/fixtures/seller_archetypes/manifest.json`

---

## Executive summary

Archetype Validation Framework infrastructure is **complete**. One of five P0 archetypes (`high_inventory_seller`) is **fully covered** via pilot user. Four archetypes have **fixture definitions only** — datasets and tenant assignments pending Phase 6.5.3.

| Coverage | Count |
|----------|-------|
| Fully covered (validated) | 1 / 5 |
| Partially covered (manifest + bands) | 4 / 5 |
| Missing scenarios | See §4 |

---

## 1. Archetype coverage matrix

| Archetype | Manifest | Metric bands | Insight rules | user_id | Dataset | Replay status |
|-----------|----------|--------------|---------------|---------|---------|---------------|
| **small_seller** | ✅ | ✅ | ✅ | ❌ | ❌ | **Partial** — fixture only |
| **seasonal_seller** | ✅ | ✅ | ✅ | ❌ | ❌ | **Partial** — fixture only |
| **unprofitable_seller** | ✅ | ✅ | ✅ | ❌ | ❌ | **Partial** — fixture only |
| **no_ads_seller** | ✅ | ✅ | ✅ | ❌ | ❌ | **Partial** — fixture only |
| **high_inventory_seller** | ✅ | ✅ | ✅ | ✅ pilot | ✅ 4 reports | **Full** — validated |

---

## 2. Fully covered archetypes

### high_inventory_seller

- **User:** `caefecb3-5789-4878-a9d4-929be573fbcc`
- **Reports:** 4 WB finance periods
- **Reference metrics:** SU 80.3, AI Readiness 86.1, Inventory Insight 100%, Echo 0%
- **Expected findings:** dead stock, frozen capital, slow movers, concentration, risk
- **Validation:** Can run `--archetype high_inventory_seller` today (requires DB)

---

## 3. Partially covered archetypes

Each has complete manifest entry (profile, bands, expected/forbidden insights) but **no assigned tenant or uploaded data**.

| Archetype | What's missing | Risk if not validated |
|-----------|----------------|----------------------|
| small_seller | ≤20 SKU dataset, user_id | Inventory noise on tiny catalog; false primary |
| seasonal_seller | Period pair ±30% delta | Revenue change analyst untested on real swing |
| unprofitable_seller | Loss-making SKUs + COGS | Profit insights may fail on negative margin |
| no_ads_seller | Zero ad-spend reports | False ad recommendations; coverage misread |

---

## 4. Missing scenarios (not in P0 manifest)

| Scenario | Priority | Notes |
|----------|----------|-------|
| Healthy stable seller | P1 | Partially covered by pilot non-peak periods |
| High-return seller | P1 | Returns >15% band untested |
| Logistics-heavy seller | P1 | Logistics >20% share |
| Concentration risk seller | P1 | Top-1 >67% |
| Report-only (no inventory snapshots) | P0 gap | `inventory_limited_signals` path |
| Seller without COGS | P1 | Trust gating / coverage floor |
| Multi-marketplace (WB + Ozon) | P2 | Deferred |
| 10+ period longitudinal | P2 | Fatigue / trend stability |

---

## 5. Infrastructure readiness

| Component | Status |
|-----------|--------|
| `manifest.json` (5 P0 archetypes) | ✅ |
| `scripts/archetype_validation.py` | ✅ |
| `scripts/archetype_audit_runner.py` | ✅ |
| `--archetype` on phase_630 / phase_622 / quality audit | ✅ |
| Unit tests (`test_archetype_manifest.py`) | ✅ |
| Framework documentation | ✅ |
| Threshold catalog linkage | ✅ |

---

## 6. Hardening risk assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| 4/5 archetypes unvalidated on real data | **High** | Phase 6.5.3 dataset + user assignment |
| Insight rules may be too strict/loose until replay | Medium | Tune manifest only (not production thresholds) |
| Pilot maps to high_inventory only | Medium | By design — other archetypes need new tenants |
| Circular import in audit scripts | Low | Lazy import in quality audit |

---

## 7. Readiness score

| Dimension | Score |
|-----------|-------|
| Framework design | 95 |
| Fixture completeness | 85 |
| Dataset coverage | 20 |
| Tooling integration | 90 |
| Documentation | 92 |

### **Archetype framework readiness: 76 / 100**

Interpretation: **Framework GO** — infrastructure ready. **Validation GO** only for `high_inventory_seller`.

---

## Related documents

- [archetype_validation_framework.md](../testing/archetype_validation_framework.md)
- [phase_652_archetype_framework_report.md](phase_652_archetype_framework_report.md)
- [mvp_hardening_plan.md](mvp_hardening_plan.md)

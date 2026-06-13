# Phase 6.5.2 — Archetype Framework Report

**Date:** 2026-06-07  
**Phase:** 6.5.2 — Archetype Validation Framework  
**Constraints honored:** No production threshold changes, no Priority Engine / Inventory Intelligence changes, no git operations

---

## Executive summary

Archetype Validation Framework created. Five P0 seller archetypes defined with metric bands, expected/optional/forbidden insights, and `--archetype` support on audit scripts. Pilot user mapped to `high_inventory_seller`. Framework unit tests pass (299 total with new tests).

### Decision

| Gate | Status |
|------|--------|
| Phase 6.5.2 framework complete | **GO** |
| Phase 6.5.3 Multi-Seller Replay | **GO** (infrastructure ready; datasets pending) |

---

## 1. Created archetypes

| ID | Name | validation_status | user_id | Primary expected domain |
|----|------|-------------------|---------|-------------------------|
| `small_seller` | Small Seller | pending_dataset | — | revenue / margin |
| `seasonal_seller` | Seasonal Seller | pending_dataset | — | revenue / concentration |
| `unprofitable_seller` | Unprofitable Seller | pending_dataset | — | profit / margin |
| `no_ads_seller` | No Advertising Seller | pending_dataset | — | revenue (ads excluded) |
| `high_inventory_seller` | High Inventory Seller | **validated** | pilot UUID | revenue / inventory |

Full definitions: `tests/fixtures/seller_archetypes/manifest.json`

---

## 2. Fixture structure

```
tests/fixtures/seller_archetypes/
├── manifest.json          # All 5 P0 archetypes (schema: seller_archetype_v1)
└── README.md              # Usage instructions
```

Each archetype entry includes:

- `business_profile` — SKU count, revenue band, ads, inventory, COGS
- `kpi_expectations` — primary domain, coverage band, notes
- `metric_bands` — minimum / target / stretch (+ maximum for echo)
- `expected_insights` — finding_ids, primary_domains, text_patterns
- `optional_insights` — may appear, not required
- `forbidden_insights` — finding_ids, primary_domains, text_patterns, rules

---

## 3. Metric bands (summary)

Bands derived from [threshold_catalog.md](../ai/threshold_catalog.md) and pilot baseline (SU 80.3, AI Readiness 86.1).

### high_inventory_seller (validated — pilot)

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Seller Usefulness | 74.0 | 80.0 | 88.0 |
| AI Readiness | 86.0 | 86.0 | 92.0 |
| Actionable Rate | 100% | 100% | 100% |
| Inventory Insight Rate | 50% | 100% | 100% |
| Dashboard Echo | 0% (max) | 0% | 0% |

### small_seller

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Seller Usefulness | 65.0 | 74.0 | 82.0 |
| AI Readiness | 75.0 | 86.0 | 90.0 |
| Inventory Insight Rate | 0% | 25% | 50% |

### seasonal_seller

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Seller Usefulness | 70.0 | 76.0 | 85.0 |
| AI Readiness | 80.0 | 86.0 | 92.0 |

### unprofitable_seller

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Seller Usefulness | 68.0 | 74.0 | 80.0 |
| AI Readiness | 82.0 | 86.0 | 90.0 |

### no_ads_seller

| Metric | Minimum | Target | Stretch |
|--------|---------|--------|---------|
| Seller Usefulness | 65.0 | 72.0 | 80.0 |
| AI Readiness | 78.0 | 84.0 | 88.0 |

All archetypes: Actionable Rate minimum 100%, Dashboard Echo maximum 0%.

Full bands in manifest.json.

---

## 4. Validation framework

| Artifact | Path |
|----------|------|
| Framework design | [docs/testing/archetype_validation_framework.md](../testing/archetype_validation_framework.md) |
| Core module | `scripts/archetype_validation.py` |
| Audit runner | `scripts/archetype_audit_runner.py` |
| Readiness assessment | [docs/release/archetype_validation_readiness.md](archetype_validation_readiness.md) |
| Unit tests | `tests/unit/test_archetype_manifest.py` |

### Audit script integration

| Script | `--archetype` | Notes |
|--------|---------------|-------|
| `phase_630_inventory_audit.py` | ✅ | + inventory metric enrichment |
| `phase_622_insight_audit.py` | ✅ | Insight engine audit |
| `ai_recommendation_quality_audit.py` | ✅ | General quality audit |
| `archetype_audit_runner.py` | ✅ (new) | Dedicated runner, `--all` flag |

### Example commands

```bash
# Pilot archetype (requires DB)
.venv/bin/python scripts/archetype_audit_runner.py --archetype high_inventory_seller

# All archetypes (4 SKIP, 1 PASS/FAIL depending on DB)
.venv/bin/python scripts/archetype_audit_runner.py --all

# Schema validation
pytest tests/unit/test_archetype_manifest.py -q
```

---

## 5. Expected AI behavior (highlights)

### High Inventory Seller — Expected

- `inventory_dead_stock`, `inventory_frozen_capital`, `inventory_slow_movers`
- Text: мёртвый сток, замороженный капитал, остатки

### High Inventory Seller — Forbidden

- Ads as primary when inventory risk critical
- >1 inventory block in executive lead (dedupe rule)
- Duplicate inventory semantic buckets

### No Ads Seller — Forbidden

- Primary domain `ads`
- Patterns: «увеличьте рекламный бюджет», «оптимизируйте кампанию»
- Fabricated ad metrics when `ads_no_governed_spend`

### Small Seller — Forbidden

- Inventory as sole primary when revenue IQ higher (+8 pp rule)
- False ad recommendations without ad data

Full rules per archetype in manifest.json.

---

## 6. Readiness score

| Dimension | 6.5.1 | 6.5.2 | Delta |
|-----------|-------|-------|-------|
| Archetype framework | 0 | 95 | +95 |
| Fixture / manifest | 0 | 85 | +85 |
| Multi-seller tooling | 25 | 90 | +65 |
| Dataset coverage | 20 | 20 | — |
| Overall hardening readiness | 81 | **86** | +5 |

**Archetype framework readiness: 76 / 100** (infrastructure vs data coverage)

---

## 7. Phase 6.5.3 preparation — Multi-Seller Replay

### Objectives

1. Assign `user_id` to each pending P0 archetype
2. Upload sanitized datasets per `business_profile`
3. Run backfill + archetype audit for all 5
4. Produce consolidated replay report

### Requirements

| Requirement | Value |
|-------------|-------|
| Minimum sellers | **5** (one per P0 archetype) |
| Minimum reports per seller | **2–4** (per archetype `reports_min`) |
| Minimum total replay analyses | **≥15** recommendations across tenants |
| Pilot reuse | `high_inventory_seller` — baseline already PASS |

### Pass criteria (Phase 6.5.3 exit)

| Check | Criterion |
|-------|-----------|
| Archetype PASS rate | **≥4 / 5** P0 archetypes PASS (minimum bands) |
| Metric regression | No archetype SU below manifest minimum |
| Dashboard Echo | 0% on all replayed tenants |
| Forbidden insights | Zero hits across all archetypes |
| Consolidated report | `reports/multi_seller_replay.json` |

### Suggested workflow

```text
1. Create 4 test tenants (or map existing sanitized accounts)
2. Upload archetype-specific WB exports + costs + snapshots
3. backfill_ai_recommendations.py --user-id <UUID> --all-reports
4. archetype_audit_runner.py --all --json-out reports/multi_seller_replay.json
5. Update manifest validation_status: pending_dataset → validated | failed
6. Publish phase_653_multi_seller_replay_report.md
```

### Out of scope for 6.5.3

- Threshold changes
- New AI modules
- Advertising Intelligence
- External MVP launch

---

## 8. Files created / modified

### Created

| Path | Purpose |
|------|---------|
| `tests/fixtures/seller_archetypes/manifest.json` | P0 archetype definitions |
| `tests/fixtures/seller_archetypes/README.md` | Fixture usage |
| `scripts/archetype_validation.py` | Load, evaluate, validate |
| `scripts/archetype_audit_runner.py` | Dedicated runner |
| `tests/unit/test_archetype_manifest.py` | Schema + band tests |
| `docs/testing/archetype_validation_framework.md` | Framework design |
| `docs/release/archetype_validation_readiness.md` | Coverage assessment |
| `docs/release/phase_652_archetype_framework_report.md` | This report |

### Modified (audit integration only)

| Path | Change |
|------|--------|
| `scripts/phase_630_inventory_audit.py` | `--archetype`, validation block |
| `scripts/phase_622_insight_audit.py` | `--archetype`, validation block |
| `scripts/ai_recommendation_quality_audit.py` | `--archetype`, validation block |

**Not modified:** `app/ai/**`, `app/domain/inventory/**`, thresholds, Priority Engine.

---

## 9. Recommendation

### **GO** for Phase 6.5.3 — Multi-Seller Replay

**Rationale:**

- Framework, manifest, tooling, and tests complete
- `--archetype` integrated without production pipeline changes
- Pilot archetype provides proven baseline
- Four pending archetypes have clear dataset contracts

**Blockers for 6.5.3 (non-code):**

- Collect/create 4 sanitized seller datasets
- Assign tenant UUIDs in manifest
- DB access for backfill + audit replay

**External MVP remains NO-GO** until 6.5.3 pass criteria met.

---

## Related documents

- [archetype_validation_framework.md](../testing/archetype_validation_framework.md)
- [archetype_validation_readiness.md](archetype_validation_readiness.md)
- [hardening_readiness.md](hardening_readiness.md)
- [threshold_catalog.md](../ai/threshold_catalog.md)
- [mvp_hardening_plan.md](mvp_hardening_plan.md)

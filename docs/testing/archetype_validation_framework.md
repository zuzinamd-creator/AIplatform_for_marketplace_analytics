# Archetype Validation Framework

**Version:** 1.0  
**Phase:** 6.5.2  
**Status:** Active — pre Multi-Seller Replay  
**Related:** [threshold_catalog.md](../ai/threshold_catalog.md), [mvp_hardening_plan.md](../release/mvp_hardening_plan.md)

---

## 1. Goals

The Archetype Validation Framework validates **existing AI intelligence** across seller business shapes **without changing production logic**.

| Goal | Description |
|------|-------------|
| Generalization proof | Demonstrate AI quality beyond single pilot user |
| Regression gate | Catch metric/insight regressions before external MVP |
| Dataset contract | Define what each seller type must upload and what AI must produce |
| Replay readiness | Prepare structured input for Phase 6.5.3 Multi-Seller Replay |

**Out of scope:** new analysts, threshold calibration, Priority Engine changes, Inventory Intelligence changes.

---

## 2. Methodology

```text
1. Define archetype (business profile + KPI expectations)
2. Assign tenant user_id + sanitized dataset (or mark pending_dataset)
3. Generate AI recommendations (existing ETL + backfill pipeline)
4. Run audit script with --archetype <id>
5. Evaluate metric bands + insight expectations
6. Record PASS | FAIL | SKIP in report JSON
```

### Validation layers

| Layer | What is checked | Source |
|-------|-----------------|--------|
| **Metric bands** | SU, AI Readiness, Actionable, Inventory Insight Rate, Dashboard Echo | Audit scripts + manifest bands |
| **Expected insights** | Required finding_ids / text patterns / primary domain | `manifest.json` |
| **Optional insights** | May appear; not required for PASS | `manifest.json` |
| **Forbidden insights** | Must not appear as primary or finding | `manifest.json` |

### Decision precedence

1. If `validation_status = pending_dataset` and no `user_id` → **SKIP**
2. If any metric below **minimum** → **FAIL**
3. If forbidden insight hit → **FAIL**
4. If no expected insight matched (when dataset present) → **FAIL**
5. Otherwise → **PASS**

**TARGET** and **STRETCH** bands are informational — only **minimum** gates FAIL.

---

## 3. Evaluation rules

### 3.1 Metric band statuses

| Status | Condition (higher-is-better metrics) |
|--------|--------------------------------------|
| FAIL | value < minimum |
| PASS | minimum ≤ value < target |
| TARGET | target ≤ value < stretch |
| STRETCH | value ≥ stretch |

**Dashboard Echo** uses inverted logic: `maximum = 0%`; any value > maximum → FAIL.

### 3.2 Insight matching

Finding IDs extracted from:

- `action_plan.insight_engine.structured_insights[].finding_id`
- `reasoning_trace.multi_layer.domain_outputs[].findings[].finding_id`

Primary domain inferred from `primary_insight` or title text.

### 3.3 PASS / FAIL criteria

| Criterion | PASS | FAIL |
|-----------|------|------|
| All metrics ≥ minimum | ✅ | ❌ |
| Dashboard Echo ≤ maximum (0%) | ✅ | ❌ |
| ≥1 expected finding_id OR expected text pattern | ✅* | ❌ |
| Zero forbidden finding_ids | ✅ | ❌ |
| Primary domain ∉ forbidden_domains | ✅ | ❌ |
| Zero forbidden text patterns (no_ads archetype) | ✅ | ❌ |

\*Waived when `validation_status = pending_dataset` (SKIP overall).

---

## 4. Expected metrics

Standard metrics evaluated for every archetype:

| Metric | Description | Typical pilot reference |
|--------|-------------|-------------------------|
| Seller Usefulness | Average `seller_usefulness_score` | 80.3 |
| AI Readiness | MVP AI composite score | 86.1 |
| Actionable Rate | % recommendations with actionable text | 100% |
| Inventory Insight Rate | % recs with inventory signals | 0–100% (archetype-dependent) |
| Dashboard Echo | % KPI restatement in primary | 0% |

Per-archetype bands: `tests/fixtures/seller_archetypes/manifest.json`

---

## 5. P0 archetypes

| ID | Name | Primary domain | Dataset status |
|----|------|----------------|----------------|
| `small_seller` | Small Seller | revenue / margin | pending_dataset |
| `seasonal_seller` | Seasonal Seller | revenue / concentration | pending_dataset |
| `unprofitable_seller` | Unprofitable Seller | profit / margin | pending_dataset |
| `no_ads_seller` | No Advertising Seller | revenue (ads excluded) | pending_dataset |
| `high_inventory_seller` | High Inventory Seller | revenue / inventory | **validated** (pilot) |

---

## 6. Tooling

### Manifest

```
tests/fixtures/seller_archetypes/manifest.json
```

### Core module

```
scripts/archetype_validation.py
```

### Runners

```bash
# Dedicated runner
.venv/bin/python scripts/archetype_audit_runner.py --archetype high_inventory_seller

# Existing audits ( --archetype added in 6.5.2 )
.venv/bin/python scripts/phase_630_inventory_audit.py --archetype high_inventory_seller --skip-migrate
.venv/bin/python scripts/phase_622_insight_audit.py --archetype high_inventory_seller --skip-migrate
.venv/bin/python scripts/ai_recommendation_quality_audit.py --archetype high_inventory_seller --json-out reports/audit.json

# All archetypes
.venv/bin/python scripts/archetype_audit_runner.py --all
```

### Unit tests

```bash
pytest tests/unit/test_archetype_manifest.py -q
```

---

## 7. Phase integration

| Phase | Deliverable |
|-------|---------------|
| 6.5.2 | Framework + manifest + `--archetype` (this document) |
| 6.5.3 | Assign user_ids, load datasets, multi-seller replay |
| 6.6.0 | External MVP gate — all P0 archetypes PASS |

---

## Related documents

- [phase_652_archetype_framework_report.md](../release/phase_652_archetype_framework_report.md)
- [archetype_validation_readiness.md](../release/archetype_validation_readiness.md)
- [hardening_readiness.md](../release/hardening_readiness.md)

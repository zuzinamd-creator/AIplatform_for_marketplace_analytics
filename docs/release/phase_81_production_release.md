# Phase 8.1 Production Release Manifest

**Codename:** Promotion Expenses MVP  
**Release tag:** `v8.1-promotion-expenses-mvp`  
**Feature baseline SHA:** `48a8d7c4246e137bdfd255f7a63bfc547e3cd436`  
**CI certification SHA (main):** `53d730b3f89c95407f148fc096c03fc98d291f05`  
**Production accepted:** 2026-07-07  
**Document date:** 2026-07-08  
**Status:** **CERTIFIED — Phase 8.1 closed**

> **Single source of truth for Production state after Phase 8.1.**  
> This document supersedes informal notes for promotion-adjusted profit scope.

---

## Official verdict

| Criterion | Status |
|-----------|--------|
| **Production = Workspace = GitHub** | ✅ Certified |
| **CI = GREEN** | ✅ Run `28944603932` @ `53d730b` |
| **AI = VALIDATED** | ✅ Phase 8.1.9 audit PASS |

**Phase 8.1 is complete and ready for closure.**

---

## 1. Release Summary

### 1.1 Features delivered in Phase 8.1

| Capability | Description |
|------------|-------------|
| **Manual promotion expenses** | Per-report `promotion_expenses` field editable by seller (PATCH API + Reports UI cell) |
| **Promotion-adjusted profit KPIs** | Primary seller profit = Profit After Promotion; Settlement Profit retained as reference |
| **Dashboard finance block** | Shows settlement profit, promotion expenses, profit after promotion, promotion impact |
| **Analytics API** | `financial_summary` and `revenue_summary` expose adjusted profit and raw settlement fields |
| **AI snapshot integration** | `seller_profit_raw`, `promotion_expenses`, `seller_profit_after_promotion`, `promotion_impact_pct` in governed metrics |
| **AI prompt contract** | `PROMOTION_PROFIT_RULES` in prompt runtime v3 — mandates correct profit interpretation |
| **Migration 0033** | `reports.promotion_expenses` column with non-negative check constraint |
| **Unit test fixtures** | Pilot-period math validation (`test_seller_kpi_math`, `test_promotion_adjusted_math`) |

### 1.2 Business problems solved

| Problem | Solution |
|---------|----------|
| Settlement profit overstated when seller runs external promotion | Overlay manual promotion expenses on settlement before COGS subtraction |
| No seller-controlled promotion input | Inline editable promotion cell on Reports page |
| AI recommendations based on pre-promotion profit | AI snapshot and prompt rules use Profit After Promotion as primary KPI |
| Dashboard showed only settlement margin | Dashboard distinguishes reference settlement vs adjusted profit |
| No audit trail for promotion impact | `promotion_impact_pct` quantifies share of settlement profit consumed by promotion |

### 1.3 Components touched

| Layer | Paths |
|-------|-------|
| Database | `alembic/versions/0033_report_promotion_expenses.py` |
| Domain | `app/domain/analytics/promotion_adjusted.py`, `seller_kpis.py`, `profit_trust.py` |
| API | `app/api/reports.py` (PATCH) |
| Services | `app/services/report_service.py`, `analytics_service.py`, `ai_service.py` |
| Schemas | `app/schemas/report.py`, `analytics.py`, `report_mappers.py` |
| Models | `app/models/report.py` |
| AI | `app/ai/prompts/v3/contracts.py`, `render.py`, `coverage/business_coverage.py` |
| Frontend | `PromotionExpensesCell.tsx`, `DashboardPage.tsx`, `ReportsPage.tsx`, state types |
| Tests | `test_promotion_adjusted_math.py`, `test_seller_kpi_math.py`, `test_migration_report_promotion_expenses.py` |
| CI (post-feature) | `.github/workflows/ci.yml` — Alembic, Ruff, integration, Docker Compose fixes |

---

## 2. Architecture Change Log

### 2.1 Backend

| Change | Detail |
|--------|--------|
| New domain module | `promotion_adjusted.py` — `compute_profit_after_promotion()`, `compute_promotion_impact_pct()` |
| Report service | `update_promotion_expenses()` — validates `>= 0`, tenant-scoped PATCH |
| Analytics service | `_sum_promotion_expenses()` aggregates per period; `_promotion_adjusted_profit()` overlays on seller KPIs |
| Financial summary | `gross_profit` = profit after promotion; `seller_profit_raw` = settlement reference |
| AI service | `_build_period_insight_bundle()` populates promotion fields in `governed_extras` |
| Report mapper | `promotion_expenses` default `Decimal("0")` when NULL |
| API route | `PATCH /api/v1/reports/{id}` with `ReportPromotionExpensesUpdate` body |

### 2.2 Frontend

| Change | Detail |
|--------|--------|
| `PromotionExpensesCell.tsx` | Inline edit component with PATCH + optimistic refresh |
| `ReportsPage.tsx` | Promotion expenses column in reports table |
| `DashboardPage.tsx` | Finance KPI block: settlement reference, promotion expenses, adjusted profit |
| `types-analytics.ts` | `seller_profit_raw`, `promotion_expenses` on finance summary |
| `types-reports.ts` | `promotion_expenses` on report row |
| `http.ts` | `api.reports.patch(reportId, { promotion_expenses })` |

### 2.3 AI

| Change | Detail |
|--------|--------|
| Prompt contract | `PROMOTION_PROFIT_RULES` — primary profit = `seller_profit_after_promotion` / `total_profit` |
| Prompt render | `PROMOTION_PROFIT_RULES` injected into system prompt (v3 runtime) |
| Snapshot fields | Four promotion KPIs + `promotion_expenses_available` flag |
| Business coverage | `_promotion_block()` activates when `promotion_expenses_available` is true |
| AI service | `total_profit` in insight input = profit after promotion, not settlement |

### 2.4 Database

| Change | Detail |
|--------|--------|
| Migration | `0033_report_promotion_expenses` |
| Column | `reports.promotion_expenses NUMERIC(18,4) NOT NULL DEFAULT 0` |
| Constraint | `ck_reports_promotion_expenses_nonneg` — `promotion_expenses >= 0` |
| Revises | `0032_lockdown_backend_tables` |

---

## 3. Database Release Section

### 3.1 Migration `0033_report_promotion_expenses`

```sql
-- Effective DDL (Alembic upgrade)
ALTER TABLE reports
  ADD COLUMN promotion_expenses NUMERIC(18,4) NOT NULL DEFAULT 0;

ALTER TABLE reports
  ADD CONSTRAINT ck_reports_promotion_expenses_nonneg
  CHECK (promotion_expenses >= 0);
```

### 3.2 New column `reports.promotion_expenses`

| Property | Value |
|----------|-------|
| Type | `NUMERIC(18,4)` |
| Nullable | `NOT NULL` |
| Default | `0` |
| Scope | Per finance report row |
| Input | Manual seller entry via PATCH API / Reports UI |
| Aggregation | `SUM(promotion_expenses)` over overlapping finance reports in period |

### 3.3 Impact on existing data

| Aspect | Behaviour |
|--------|-----------|
| Existing reports | Backfilled with `0` via `server_default` — no data loss |
| Existing KPIs | Unchanged when `promotion_expenses = 0` (profit after = settlement profit) |
| Rollback | `downgrade()` drops constraint and column |
| Production deploy | `alembic upgrade head` required before API serves PATCH |

---

## 4. Business Logic Section

### 4.1 Profit formulas

**Settlement (reference only):**

```
total_to_pay     = payout_for_goods − logistics − storage − deductions
seller_profit_raw = total_to_pay − COGS
```

**Promotion-adjusted (primary KPI):**

```
adjusted_settlement           = total_to_pay − promotion_expenses
seller_profit_after_promotion = adjusted_settlement − COGS
```

**Promotion impact:**

```
promotion_impact_pct = (seller_profit_raw − seller_profit_after_promotion) × 100 / seller_profit_raw
                     (only when seller_profit_raw > 0)
```

**Margin / profitability** after promotion are recomputed on `seller_profit_after_promotion`.

### 4.2 Settlement Profit vs Profit After Promotion

| Metric | Meaning | UI role |
|--------|---------|---------|
| **Settlement Profit** (`seller_profit_raw`) | WB settlement minus COGS, before external promotion overlay | Reference — «Прибыль до учёта продвижения» |
| **Profit After Promotion** (`seller_profit_after_promotion`, `total_profit`, `gross_profit`) | Settlement minus manual promotion expenses minus COGS | **Primary** — «Чистая прибыль» |
| **Promotion Expenses** | Seller-entered external promotion spend per report | Editable input |
| **Promotion Impact** | Percentage of settlement profit consumed by promotion | Diagnostic KPI |

### 4.3 Promotion impact interpretation

- Measures how much of settlement profit is absorbed by manually entered promotion costs.
- Does **not** double-count WB ledger `deductions` — promotion is a separate overlay for external/ad spend the seller tracks outside standard settlement lines.
- When `promotion_expenses = 0`, impact is omitted and all profit KPIs equal settlement profit.

---

## 5. Production Acceptance Section

**Pilot period:** 2026-06-29 — 2026-07-05 (WB finance, pilot seller)  
**Validation source:** Production UI + unit test fixture `PILOT_EXPECTED` / `test_promotion_adjusted_math.py`

| KPI | Production value | Verified |
|-----|------------------|----------|
| Settlement Profit | **100 530.15 ₽** | ✅ |
| Promotion Expenses | **9 925.00 ₽** | ✅ |
| Profit After Promotion | **90 605.15 ₽** | ✅ |
| Promotion Impact | **9.87 %** | ✅ |

**Cross-check:**

```
100 530.15 − 9 925.00 = 90 605.15  ✓
(9 925 / 100 530.15) × 100 = 9.87 %  ✓
```

**Production bundle (tag metadata):** `index-ZFTkPRsI.js`  
**Production accepted:** 2026-07-07

---

## 6. Git Release Section

### 6.1 Commits

| Role | SHA | Message |
|------|-----|---------|
| **Feature baseline (tagged)** | `48a8d7c` | `feat(finance): add promotion expenses MVP with adjusted profit KPIs` |
| **CI / lint recovery** | `1330cb0` | `fix(ci): resolve Ruff and mypy errors for green GitHub Actions` |
| **CI infrastructure** | `f3883a9` … `53d730b` | Alembic env, integration tests, Docker Compose validation |
| **Main HEAD (CI green)** | `53d730b` | `ci: fix docker compose validation in GitHub Actions` |

### 6.2 Release tag

| Tag | Points to | Annotated message |
|-----|-----------|-------------------|
| `v8.1-promotion-expenses-mvp` | `48a8d7c` | Phase 8.1 — Promotion Expenses MVP; Production accepted 2026-07-07; Migration 0033 |

### 6.3 GitHub verification

| Check | Result |
|-------|--------|
| `origin/main` | `53d730b` — synced with workspace |
| Tag on remote | `v8.1-promotion-expenses-mvp` present |
| Feature commit on main | `48a8d7c` is ancestor of `53d730b` |
| Production feature integrity | Tag immutable at feature SHA; CI fixes are infrastructure-only |

---

## 7. CI Certification Section

**Run ID:** `28944603932`  
**Workflow:** CI  
**Commit:** `53d730b3f89c95407f148fc096c03fc98d291f05`  
**Conclusion:** `success`  
**Completed:** 2026-07-08T13:05:14Z

| Step | Status |
|------|--------|
| Architecture governance (light) | ✅ success |
| Ruff | ✅ success |
| Mypy | ✅ success |
| Alembic upgrade | ✅ success |
| Unit tests | ✅ success (355 passed) |
| Integration tests | ✅ success (47 passed, 2 skipped) |
| Docker Compose config | ✅ success |

**CI = GREEN — certified 2026-07-08 (Phase 8.1.8.4.1).**

---

## 8. AI Validation Section

**Audit phase:** 8.1.9  
**Verdict:** **AI VALIDATED**

### 8.1 Snapshot audit — PASS

Full path: `Report.promotion_expenses` + `_wb_seller_kpis` → `compute_profit_after_promotion` → `_build_period_insight_bundle` → `build_grounded_context` → `metrics_snapshot`.

All four fields present in pilot snapshot:

| Field | Pilot value |
|-------|-------------|
| `seller_profit_raw` | 100530.15 |
| `promotion_expenses` | 9925 |
| `seller_profit_after_promotion` | 90605.15 |
| `promotion_impact_pct` | 9.87 |

### 8.2 Prompt audit — PASS

`PROMOTION_PROFIT_RULES` confirmed in system prompt via `render_prompt_v3()`. Rules mandate:

- Primary profit = `seller_profit_after_promotion` / `total_profit`
- Settlement (`seller_profit_raw`) = reference only
- Four-line Russian summary structure when `promotion_expenses > 0`

### 8.3 Recommendation sensitivity — PASS

| Scenario | promotion | profit_after | impact % | coverage score |
|----------|-----------|--------------|----------|----------------|
| A | 0 | 100 530.15 | — | 26.0 |
| B | 5 000 | 95 530.15 | 4.97 % | 38.0 |
| C | 15 000 | 85 530.15 | 14.92 % | 38.0 |

Deterministic layers (snapshot, business coverage) respond to promotion changes.

### 8.4 Hallucination audit — PASS (with residual watch)

| Risk | Mitigation |
|------|------------|
| Settlement called «чистая прибыль» | Prompt explicitly maps «Чистая прибыль» → `seller_profit_after_promotion` |
| Mixing settlement and adjusted profit | Separate snapshot keys + prompt labels |
| Promotion as COGS | Promotion is settlement overlay, COGS unchanged |
| Ignoring impact % | Field computed and included in prompt template |

**Residual watch (non-blocking):** legacy `seller_profit` snapshot key mirrors settlement value; mitigated by `PROMOTION_PROFIT_RULES`.

---

## 9. Known Limitations Section

### 9.1 Current limitations

| ID | Limitation |
|----|------------|
| L-01 | Promotion expenses are **manual per report** — no WB Ads API auto-import |
| L-02 | Promotion overlay does not modify ledger — read-layer adjustment only |
| L-03 | `promotion_expenses` aggregated by report period overlap, not by operation_date |
| L-04 | AI LLM compliance depends on prompt adherence; mock provider does not echo promotion in tests |
| L-05 | Legacy `seller_profit` key in AI snapshot = settlement (not after promotion) |
| L-06 | Single pilot seller validated in production; multi-seller promotion patterns unverified |

### 9.2 Technical debt (carried forward)

| ID | Item | Target |
|----|------|--------|
| TD-H01 | Single-seller AI validation | v0.7+ |
| TD-H02 | Hardcoded AI thresholds | v0.7.1 |
| TD-8.1-01 | Rename/remove legacy `seller_profit` in AI snapshot | Phase 8.2 |
| TD-8.1-02 | WB Ads / external marketing auto-import for promotion | Phase 8.2+ |
| TD-8.1-03 | Promotion sensitivity integration test with real LLM provider | Phase 8.2 |

### 9.3 Future phase candidates

- Auto-import promotion from WB advertising reports
- Per-SKU promotion allocation
- Promotion ROI / ROMI in AI analyst findings
- Multi-seller promotion validation replay
- Tag `v8.1.1` or `v8.2` when CI fixes are tagged separately from feature baseline

---

## 10. Final Production Certification

### Certification checklist

| # | Criterion | Evidence | Status |
|---|-----------|----------|--------|
| 1 | Feature deployed to production | Pilot KPIs accepted 2026-07-07 | ✅ |
| 2 | Migration 0033 applied | Production DB + Alembic CI pass | ✅ |
| 3 | Frontend bundle live | `index-ZFTkPRsI.js` per tag metadata | ✅ |
| 4 | GitHub = source of truth | `main` @ `53d730b`, tag `v8.1-promotion-expenses-mvp` | ✅ |
| 5 | Workspace synced | No uncommitted feature drift | ✅ |
| 6 | CI green | Run `28944603932` all steps success | ✅ |
| 7 | AI validated | Phase 8.1.9 audit PASS | ✅ |
| 8 | Math verified | Pilot fixture + production cross-check | ✅ |
| 9 | Release documentation | This manifest | ✅ |

### Signed verdict

```
╔══════════════════════════════════════════════════════════════╗
║  PHASE 8.1 — PROMOTION EXPENSES MVP                          ║
║                                                              ║
║  Production  = Workspace = GitHub          ✅ CERTIFIED        ║
║  CI          = GREEN                       ✅ CERTIFIED        ║
║  AI          = VALIDATED                   ✅ CERTIFIED        ║
║                                                              ║
║  Phase 8.1 COMPLETE — READY FOR CLOSURE                      ║
╚══════════════════════════════════════════════════════════════╝
```

**Certified by:** Phase 8.1.10 Release Documentation audit  
**Date:** 2026-07-08

---

## Appendix A — Phase 8.1 commit timeline

| Phase | SHA | Description |
|-------|-----|-------------|
| 8.1.0 | `48a8d7c` | Promotion Expenses MVP feature |
| 8.1.8 | `1330cb0` | Ruff + mypy CI recovery |
| 8.1.8 | `f3883a9`–`0c91130` | Alembic + integration test fixes |
| 8.1.8.4 | `1bdc163` | Docker Compose `--quiet` fix |
| 8.1.8.4.1 | `53d730b` | Docker Compose `.env` fix — CI GREEN |
| 8.1.9 | — | AI validation audit (read-only) |
| 8.1.10 | — | This release manifest |

## Appendix B — Key file reference

| Purpose | Path |
|---------|------|
| Profit math | `app/domain/analytics/promotion_adjusted.py` |
| Seller settlement | `app/domain/analytics/seller_kpis.py` |
| AI snapshot builder | `app/services/ai_service.py` (`_build_period_insight_bundle`) |
| AI prompt rules | `app/ai/prompts/v3/contracts.py` (`PROMOTION_PROFIT_RULES`) |
| Migration | `alembic/versions/0033_report_promotion_expenses.py` |
| Pilot math tests | `tests/unit/test_promotion_adjusted_math.py` |
| CI workflow | `.github/workflows/ci.yml` |

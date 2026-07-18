# Changelog

## [9.16-D] — 2026-07-18 — Documentation reconciliation

### Changed
- README + docs hub aligned to production baseline `7f65cfb` / bundle `DVVPbWvu`.
- Seller dashboard, Insight Engine V1, and margin semantics documented.

### Added
- `docs/release/phase_916c_production_baseline.md`
- `docs/product/dashboard_insight_engine.md`
- `docs/product/margin_semantics.md`
- Rewrote `docs/frontend/seller_dashboard.md`

---

## [9.16-C] — 2026-07-18 — Seller feedback P0 (Insight Engine V1)

### Added
- **Insight Engine V1** — deterministic Fact + Driver + Attention captions on revenue, cost structure, daily costs, Top SKU (`chart-insights.ts`).
- Margin labels + static hints: **Маржа по выплате**, **Маржа SKU**, **Маржа (юнит-экономика)**.
- Period share strip and «% — доля от общей суммы расходов за период» under cost charts.

### Changed
- Financial Summary: flat **Расходы WB** (commission → logistics → storage → deductions); removed «Детализация услуг WB» accordion.
- Daily costs subtitle documents total-cost formula (returns excluded).

### Constraints
- No backend profit formula changes; no AI-generated insights.
- Production: `7f65cfb` · FE `index-DVVPbWvu.js`.

---

## [9.15] — 2026-07-17 — Seller feedback (commission, total daily costs, captions)

### Added
- Financial Summary **Комиссия WB** row; removed standalone «Прибыль» heading.
- Daily chart **Общие затраты по дням** = sum of eight fee categories (excludes returns).
- Early deterministic one-line chart captions (superseded by 9.16-C Insight Engine V1).
- Top SKU label **Маржа SKU**.

### Production
- Commit `0579f09` · bundle `index-BUMXPZet.js`.

---

## [9.14] — 2026-07-16 — Seller feedback UX (readability & cost structure)

### Changed
- Top SKU: full name wrapping / vertical metrics layout.
- Cost structure: period composition view + clearer copy.
- Financial Summary footer / disclosure cleanup.

### Production
- Commit `8b04dff` (line continued into 9.15/9.16).

---

## [9.8-B] — 2026-07-12 — Analytics Hub Polish & Dedup

### Changed
- **Inventory dedup** — Comparison keeps summary KPIs, priorities, warehouse; SKU tables replaced with CTA to Inventory Economics.
- **Dashboard soft redirect** — `/app` and `/app/dashboard` → `/app/analytics` (query/hash preserved); nav «Панель» → hub.
- **Shared period context** — `AnalyticsPeriodProvider` + `usePagePeriod` across hub tabs.

### Added
- `frontend/src/shell/analytics-period-context.tsx`, `DashboardRedirect.tsx`, `use-page-period.ts`
- `docs/product/analytics_hub_polish.md`

### Constraints respected
- No KPI, API, trust, AI, or backend changes; all legacy routes work via redirect.

---

### Added
- **`AnalyticsShell`** — tab shell at `/app/analytics` embedding Overview, Comparison, Economics, and Cost Coverage.
- Hub route aliases: `/app/analytics/economics`, `/app/analytics/cost-coverage`, `/app/analytics/overview` → `/app/analytics`.
- `FEATURE_FLAGS.analyticsHubTabs` — rollback to 9.7-C link hub when `false`.
- `frontend/src/shell/analytics-tabs.ts` — shared tab definitions and route constants.
- `docs/release/phase_98a_certification.md` — deployment certification.

### Changed
- **Navigation** — Analytics Hub (`/app/analytics`) is the primary analytics entry; cost coverage moved from Reports to Analytics section.
- **Cross-links** — Comparison and Economics CTAs use hub tab routes.
- Legacy routes preserved: `/app/dashboard`, `/app/analytics/weekly`, `/app/economics`, `/app/finance/cost-coverage`.

### Constraints respected
- No KPI calculation, API, trust threshold, or AI prompt changes.
- No route removal; backward-compatible bookmarks.

---

### Validated
- **PARTIAL trust live** — dedicated tenant `partial-trust-e2e@mail.ru` at 50% COGS coverage (1/2 SKUs).
- **7/7 UX Scenario B steps** — Dashboard, Comparison, Economics, SKU Drilldown, Reconciliation, Cost Coverage, AI Recommendations.
- **Trust upgrade journey** — partial (50%) → COGS upload → full (100%) confirmed.

### Added
- `docs/product/partial_trust_validation_results.md` — live API evidence and UX walkthrough results.
- `docs/release/phase_97e_certification.md` — **GO** for Phase 9.8-A Analytics Hub physical merge.

### Defects
- Medium (documented): CSV cost import requires quoted fields for SKU names containing commas — no code fix.

### Decision
- **GO** for Phase 9.8-A — all three trust states (INSUFFICIENT, PARTIAL, FULL) live-validated.

---

## [9.7-D] — 2026-07-11 — Trust Closure & Analytics Hub Preparation

### Fixed
- **Reconciliation profit trust gate** — `ReconciliationService` applies `apply_profit_trust_to_kpis`; `breakdown.profit` is `null` when trust is insufficient.
- **Reconciliation integrity** — `GET /analytics/reconciliation/period` now returns `integrity` with `profit_metrics_trust`.

### Changed
- **ReconciliationPage** — trust sourced from reconciliation API (removed redundant revenue summary fetch for trust).
- **API contract:** `ReconciliationBreakdown.profit: Decimal | None`.

### Added
- `docs/product/trust_matrix_certification.md` — consolidated FULL / PARTIAL / INSUFFICIENT surface matrix.
- `docs/product/partial_trust_live_validation.md` — production-safe PARTIAL validation procedure.
- `docs/product/analytics_hub_master_spec.md` — unified hub architecture, 9.8 scope, rollback strategy.
- `tests/unit/test_reconciliation_trust.py` — reconciliation profit gating contract tests.

---

## [9.7-C] — 2026-07-11 — Analytics Hub Step 2 (IA Refactoring)

### Added
- `/app/analytics` — `AnalyticsHubPage` entry with links to Overview, Comparison, Economics, Cost Coverage.
- Comparison → Economics and Cost Coverage header CTAs.
- Economics → Cost Coverage header CTA.
- Cost Coverage → Analytics back-link.

### Changed
- Dashboard overview: removed inline Δвыручка compare teaser; no compare API params.
- Nav section headers: Обзор / Аналитика / Отчеты (Russian).
- Analytics nav: «Обзор аналитики» → `/app/analytics`.

### Docs
- `docs/product/analytics_hub_step2.md`

---

## [9.7-B] — 2026-07-11 — Trust UX Pilot Validation

### Added
- `docs/product/trust_ux_validation_report.md` — FULL/INSUFFICIENT live validation, PARTIAL staging procedure, hub readiness 76/100.

### Validated
- **INSUFFICIENT** live tenant `mvp-e2e-test@mail.ru` — API + trust UX PASS.
- **FULL** live tenant `margarita.zuzina@mail.ru` — 46/46 COGS, profit/margin/delta PASS.
- **PARTIAL** — unit/code path PASS; live staging procedure documented (no production tenant).

### Decision
- **Conditional GO** for Phase 9.7-C (Analytics Hub Step 2) after PARTIAL staging walkthrough.

---

## [9.7-A] — 2026-07-11 — Backend Trust Hardening

### Fixed
- **`period_compare` `delta_profit` null→0 coercion** — backend returns `null` when either period profit is unavailable (`compute_period_compare_delta_profit`).
- **Client-side profit deltas** — `computeClientProfitDelta` / `computeClientMarginDelta` guard Economics and SKU Drilldown compare modes (no `?? 0` coercion).
- **Weekly Analysis priorities** — profit-decline alert uses guarded `delta_profit`.

### Changed
- **API contract:** `PeriodComparisonResponse.delta_profit` is now `Decimal | None`.
- **Frontend types:** `delta_profit: string | null`.

### Added
- `docs/product/pilot_trust_validation.md` — FULL / PARTIAL / INSUFFICIENT pilot scenarios.
- Backend unit test `test_compute_period_compare_delta_profit`.
- Integration test `test_period_compare_delta_profit_null_when_profit_unavailable`.
- Frontend tests for `computeClientProfitDelta` / `computeClientMarginDelta`.

---

## [9.6B-3] — 2026-07-10 — Trust UX Completion

### Added
- **9.6B-3 Trust UX Completion** — dashboard trust integration, global banner enabled, reconciliation/cost-coverage/AI disclosure, chart null→0 hardening, `CostTrustDisclosure`, `chartTrustNumeric`.

---

## [9.6B-2A] — 2026-07-10 — Production Deployment & Trust Validation

### Deployed
- Frontend trust integration (9.6B-2) to production VPS — bundle `index-BqjAbDai.js`
- Post-deploy smoke test PASS; DEPLOY == GIT certified at `7aedd90`
- Certification: [docs/release/phase_96b2a_deployment_certification.md](docs/release/phase_96b2a_deployment_certification.md)

---

## [Unreleased] — Phase 9.6B-2 Trust Integration (2026-07-10)

### Added
- **9.6B-2 Trust Integration** — trust layer on WeeklyAnalysisPage, EconomicsPage, SkuDrilldownPage; `TrustDeltaBadge`, `guardPeriodCompareDeltaProfit`, `useCostTrustShellData`; nav label «Покрытие себестоимости»; `docs/product/cost_trust_system.md`.

---

## [Unreleased] — Phase 9.6B-1 Trust Foundation (2026-07-10)

### Added
- **9.6B-1 Trust Foundation** — frontend Cost Trust System: `useProfitTrust`, `ProfitTrustBadge`, `CostCoverageIndicator`, `CostTrustBanner`; trust-gated profit/margin formatting; unit tests; README and frontend architecture docs.

---

## [Unreleased] — Phase 5 (2026-06-06)

### Fixed
- **GET /reports → 500**: missing `func` import in `ReportService._latest_jobs_for_reports`.
- **Revenue canonical definition**: return rows no longer emit spurious `SALE` ledger entries (+return retail was double-counted in revenue).
- **Cost import v1**: `bulk_import` now triggers financial projection rebuild (was silent stale profit).
- **Retail column mapping**: prefer gross retail price columns over SPP/discount columns when both exist.

### Added
- **Cost history delete**: `DELETE /costs/{id}` with confirmation in UI; rebuilds coverage and financial projections.
- **ETL logging**: structured `report_upload_enqueued` on successful upload queue.
- **Tests**: cost delete effective-dating, report service import regression, return-row revenue guard.

### Documentation
- README: official analytics period rule (sale dates), revenue definition, upload pipeline diagram.
- Reconciliation remains internal-only for MVP.

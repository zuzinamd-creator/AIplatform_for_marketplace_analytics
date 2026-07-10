# Changelog

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

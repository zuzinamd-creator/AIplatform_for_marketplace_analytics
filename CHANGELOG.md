# Changelog

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

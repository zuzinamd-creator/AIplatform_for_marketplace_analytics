# Phase 9.18-D1 — Production Deployment & HTTPS Certification

**Date:** 2026-07-20 (UTC)  
**Code:** Phase 9.18-D P1 (A+B+C+D)  
**Impl commit:** `3fc685e18564223d57ced29da3f68fc85fdd0a7c`

## Pre-deploy scope

Only 9.18-D files: `security_context`, `dashboard_service`, `dashboard_query_cache` (new), `analytics_service` (cache hooks), `cost_coverage_service` (shared freshness), `ops_service` (`_tenant_read` skip), unit tests.  
No KPI/formula/domain/schema/`DashboardSummaryResponse` changes.

## Deploy

| Item | Value |
|------|-------|
| Restart | `marketplace-backend` + `marketplace-worker` |
| Backend ActiveEnter | 2026-07-20 05:44:43 UTC |
| Worker ActiveEnter | 2026-07-20 05:44:45 UTC |
| Health | `{"status":"ok"}` |
| FE bundle | unchanged `index-0fnrG7B4.js` (no FE source change) |

## HTTPS performance (production)

Endpoint: `GET https://321997.fornex.cloud/api/v1/dashboard/summary`  
Period: `2026-07-06` … `2026-07-12` · marketplace `wildberries` · **5 warmed samples**

### Admin (pilot `caefecb3`)

| Metric | Before (9.18-D pre-deploy / 9.18-B) | After |
|--------|-------------------------------------:|------:|
| HTTPS latency median | ~4161 ms (9.18-B) / ~5763 ms (pre-D spike) | **1737 ms** |
| HTTPS best / worst / p95 | — | **1532 / 2041 / 2041** |
| SQL count* | 359 | **85** |
| `set_config`* | 208 | **30** |
| `runtime_summary`* | 8 | **1** |
| `validate_period`* | 6 | **1** |

\*SQL/`set_config`/call counts measured on deployed code path (`DashboardService`) against production DB (same fan-out as HTTPS backend).

### Seller path

| Metric | Before | After |
|--------|-------:|------:|
| HTTPS latency median | ~4–5 s class (pre-P1) | **1382 ms** (`newuser@example.com`, empty tenant) |
| Service-path SQL* (pilot data, seller role) | 330 | **70** |
| `set_config`* | 196 | **24** |
| `runtime_summary`* | 7 | **1** |
| `validate_period`* | 6 | **1** |

Pilot-tenant HTTPS as seller is not available (pilot is `platform_admin`); seller **code path** counters use role override on pilot data; seller **HTTPS** uses an active seller account (empty analytics → smaller payload, still exercises slim fan-out).

Localhost deployed backend (admin): median **1723 ms** (aligns with HTTPS).

## Functional

Admin HTTPS payload: KPIs present, Top SKU n=5, revenue/finance trends n=7, coverage/cost_coverage present, slim `priority_queue=[]`, schema keys unchanged, HTTP 200.

## Identity

Operators: `git rev-parse HEAD` / stamps under `/var/lib/marketplace-analytics/` — tip at certification close equals impl SHA until docs tip (if any).

## Verdict

**GO** — production HTTPS median **~1.7 s** (admin pilot) inside **1.8–2.5 s** target. No functional regressions observed. Ready for Premium UI Audit.

# Phase 9.6B-3 — Production Deployment & Trust UX Completion

**Date:** 2026-07-10  
**Host:** `321997.fornex.cloud`  
**Git HEAD (deployed):** `255bd2ac05324d7131c2475ec44cbd310a897b64`  
**Previous certified baseline:** `7aedd903ecf03c1e96bacff14ce378b07f35d1cc`  
**Frontend bundle:** `index-B1kahpoB.js` (1 046 084 bytes)  
**CSS bundle:** `index-CNue-qzr.css`  
**Deploy timestamp (UTC):** 2026-07-10T20:34Z  

---

## 1. Pre-deploy audit

| Check | Value |
|-------|-------|
| Branch | `main` |
| Git HEAD | `255bd2ac05324d7131c2475ec44cbd310a897b64` |
| Certified tag (pre-deploy) | `7aedd903ecf03c1e96bacff14ce378b07f35d1cc` |
| Delta | +1 commit (9.6B-3 trust UX completion) |
| Working tree | Allowlisted artifacts only (`tsbuildinfo`, untracked tmp/screenshots) — deploy guard PASS |

---

## 2. Deployment

**Command:** `bash scripts/deploy-frontend.sh`

| Step | Result |
|------|--------|
| Deploy guard (git + RAM) | PASS |
| `npm test` (pre-commit) | PASS (66/66) |
| `npm run build` | PASS (2788 modules) |
| rsync → `/var/www/marketplace-analytics` | PASS |
| nginx static | `index.html` @ 2026-07-10 20:34 UTC |

**Scope:** Frontend only — no backend restart, no Alembic, no business-logic changes.

---

## 3. Post-deploy smoke test

**Command:** `bash scripts/post_deploy_smoke_test.sh`  
**Result:** **PASS** (0 failures; 1 transient 500 on first run, PASS on retry)

| Check | Status |
|-------|--------|
| systemd backend/worker/orchestrator/nginx | OK |
| `/health`, `/health/ready` | OK |
| Auth login + `/auth/me` | OK |
| `/reports`, `/costs`, `/dashboard/summary` | OK |
| Frontend `GET /` | OK |

---

## 4. Trust UX validation (9.6B-3)

### Bundle verification (production JS)

Trust UI strings present in `index-B1kahpoB.js`:

- `Проверено` (full)
- `Оценка` (partial)
- `Нет себестоимости` (insufficient)
- `Доверие к прибыли` (global banner)
- `Покрытие себестоимости` (nav + CTAs)

### Global banner

| Check | Status |
|-------|--------|
| `FEATURE_FLAGS.costTrustBannerGlobal` | `true` |
| Inline banner dedup (`showInlineCostTrustBanner`) | Enabled on all financial pages |
| Dismiss persistence | Session storage (existing `CostTrustBanner` behavior) |

### Surface checklist (9.6B-3)

| Surface | Deployed | Trust integrated |
|---------|----------|------------------|
| DashboardPage | ✅ | Hero/finance KPI badges, coverage bar, chart `chartTrustNumeric` |
| ReconciliationPage | ✅ | Profit KPI `ProfitTrustBadge` |
| CostCoveragePage | ✅ | Trust context, badges, CTA consistency |
| RecommendationsPage | ✅ | `CostTrustDisclosure` |
| RecommendationDetailPage | ✅ | `CostTrustDisclosure` + `AiTrustPanel` cost badge |
| Global banner | ✅ Enabled | `CostTrustBannerMount` in AppShell |

### Trust level matrix

| Level | Live production | Unit tests | Doc alignment |
|-------|-----------------|------------|---------------|
| **insufficient** | Validated (MVP tenant API + bundle) | `profit-trust.test.ts` + page tests | ✅ |
| **partial** | Not live (no tenant with 1–99% coverage on VPS) | Component + page tests | ✅ |
| **full** | Not live (MVP tenant has 0 SKUs / no COGS) | `profit-trust.test.ts` | ✅ |

**Note:** FULL and PARTIAL browser walkthrough requires pilot seller with COGS data — deferred to Phase 9.7 pilot session.

---

## 5. DEPLOY == GIT certification

| Field | SHA / artifact |
|-------|----------------|
| **Git HEAD (VPS workspace)** | `255bd2ac05324d7131c2475ec44cbd310a897b64` |
| **Production frontend build source** | `255bd2ac05324d7131c2475ec44cbd310a897b64` (deploy from workspace HEAD) |
| **Production JS hash (nginx)** | `index-B1kahpoB.js` |
| **certified-production tag (post-cert)** | `255bd2ac05324d7131c2475ec44cbd310a897b64` |

**Verdict:** **DEPLOY == GIT** ✅ (frontend runtime matches Git HEAD)

Backend process code unchanged since 9.6B-2A — frontend-only release.

---

## 6. Certification decision

| Gate | Result |
|------|--------|
| Deploy | PASS |
| Smoke test | PASS |
| Trust bundle + insufficient live | PASS |
| Global banner enabled | PASS |
| Dashboard / reconciliation / AI disclosure | PASS |
| DEPLOY == GIT | PASS |

**Decision:** **GO** for Phase 9.7 (backend delta_profit fix, pilot FULL/PARTIAL browser validation)

**Residual for 9.7:**

1. Backend: return `null` delta_profit when profit unavailable (`analytics_service.period_compare`)
2. Pilot seller browser validation for FULL / PARTIAL trust states
3. Optional: cost-trust integration tests against live pilot tenant

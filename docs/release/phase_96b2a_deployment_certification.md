# Phase 9.6B-2A — Production Deployment & Trust Validation

**Date:** 2026-07-10  
**Host:** `321997.fornex.cloud`  
**Git HEAD (deployed):** `7aedd903ecf03c1e96bacff14ce378b07f35d1cc`  
**Previous certified baseline:** `f5c018bb5c461b3f35afe7b28a4ddab58381e670`  
**Frontend bundle:** `index-BqjAbDai.js` (1 039 814 bytes)  
**CSS bundle:** `index-CNue-qzr.css`  
**Deploy timestamp (UTC):** 2026-07-10T20:04Z  

---

## 1. Pre-deploy audit

| Check | Value |
|-------|-------|
| Branch | `main` |
| Git HEAD | `7aedd903ecf03c1e96bacff14ce378b07f35d1cc` |
| Certified tag (pre-deploy) | `f5c018bb5c461b3f35afe7b28a4ddab58381e670` |
| Delta | +2 commits (9.6B-1 + 9.6B-2 frontend trust) |
| Working tree | Allowlisted artifacts only (`tsbuildinfo`, untracked tmp/screenshots) — deploy guard PASS |

---

## 2. Deployment

**Command:** `bash scripts/deploy-frontend.sh`

| Step | Result |
|------|--------|
| Deploy guard (git + RAM) | PASS |
| `npm run build` | PASS (2787 modules) |
| rsync → `/var/www/marketplace-analytics` | PASS |
| nginx static | `index.html` @ 2026-07-10 20:04 UTC |

**Scope:** Frontend only — no backend restart, no Alembic, no business-logic changes.

---

## 3. Post-deploy smoke test

**Command:** `bash scripts/post_deploy_smoke_test.sh`  
**Result:** **PASS** (0 failures)

| Check | Status |
|-------|--------|
| systemd backend/worker/orchestrator/nginx | OK |
| `/health`, `/health/ready` | OK |
| Auth login + `/auth/me` | OK |
| `/reports`, `/costs`, `/dashboard/summary` | OK |
| Frontend `GET /` | OK |

**Route availability (SPA, HTTP 200):**

- `/app/dashboard`
- `/app/analytics/weekly`
- `/app/economics`
- `/app/finance/cost-coverage`

---

## 4. Trust UX validation

### Bundle verification (production JS)

Trust UI strings present in `index-BqjAbDai.js`:

- `Проверено` (full)
- `Оценка` (partial)
- `Нет себестоимости` (insufficient)
- `Недостаточно данных` (SKU gating)
- `Доверие к прибыли` (banner)
- `Покрытие себестоимости` (nav CTA)

### Live API (MVP test tenant)

Period: 2026-06-29 → 2026-07-05 · marketplace: wildberries

| Signal | Value | Expected UI |
|--------|-------|-------------|
| `profit_metrics_trust` | `insufficient` | Banner, badges «Нет себестоимости», profit hidden |
| `a.total_profit` / `b.total_profit` | `null` / `null` | — |
| `delta_profit` (backend) | `0` | Frontend guard → `н/д` (not misleading zero) |
| SKU economics items | 0 | Empty state (no false profitable/unprofitable) |

### Trust level matrix

| Level | Live production | Unit tests | Doc alignment |
|-------|-----------------|------------|---------------|
| **insufficient** | Validated (MVP tenant API + bundle) | 19 tests in `profit-trust.test.ts` | ✅ |
| **partial** | Not live (no tenant with 1–99% coverage on VPS) | Covered in component + page tests | ✅ |
| **full** | Not live (MVP tenant has 0 SKUs / no COGS) | Covered in `profit-trust.test.ts` | ✅ |

**Note:** FULL and PARTIAL require pilot seller with COGS data for browser walkthrough — deferred to 9.6B-3 pilot session. Code paths and bundle strings certified.

### Surface checklist (9.6B-2)

| Surface | Deployed | Trust integrated |
|---------|----------|------------------|
| WeeklyAnalysisPage | ✅ | Banner, badges, delta guard, priority gating |
| EconomicsPage | ✅ | Banner, column badges, SKU status gating |
| SkuDrilldownPage | ✅ | Banner, KPI badges, chart gating |
| CostCoveragePage | ✅ | Route loads (200) |
| Global banner | Disabled (`costTrustBannerGlobal: false`) | Wired, not enabled |

---

## 5. DEPLOY == GIT certification

| Field | SHA / artifact |
|-------|----------------|
| **Git HEAD (VPS workspace)** | `7aedd903ecf03c1e96bacff14ce378b07f35d1cc` |
| **Production frontend build source** | `7aedd903ecf03c1e96bacff14ce378b07f35d1cc` (same commit, deploy from workspace HEAD) |
| **Production JS hash (nginx)** | `index-BqjAbDai.js` |
| **certified-production tag (post-cert)** | `7aedd903ecf03c1e96bacff14ce378b07f35d1cc` |

**Verdict:** **DEPLOY == GIT** ✅ (frontend runtime matches Git HEAD)

Backend process code unchanged since prior baseline — frontend-only release.

---

## 6. Certification decision

| Gate | Result |
|------|--------|
| Deploy | PASS |
| Smoke test | PASS |
| Trust bundle + insufficient live | PASS |
| DEPLOY == GIT | PASS |

**Decision:** **GO** for Phase 9.6B-3 (global banner enable, dashboard trust, backend delta_profit fix)

**Conditions for 9.6B-3:**

1. Pilot seller browser validation for FULL / PARTIAL trust states
2. Enable `FEATURE_FLAGS.costTrustBannerGlobal` after pilot sign-off
3. Backend: return `null` delta_profit when profit unavailable (residual risk documented)

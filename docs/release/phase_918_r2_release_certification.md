# Phase 9.18-R2 — Release Execution & Production Certification

**Date:** 2026-07-20 (UTC)  
**Decision:** **GO**

## Identity

| Pointer | Value |
|---------|-------|
| F2 code tip (FE publish) | `49f843f3609fefab166828afcbf46ebc3bd5e59b` |
| Rollback SHA | `11affb419d5a89ccde451928a20bc6e7254c265c` |
| Rollback bundle | `index-0fnrG7B4.js` (saved under `/tmp/r2-rollback-www`) |
| Deployed bundle | `index-CfF3RxW0.js` |
| Bundle SHA-256 | `beeeda2c3d73850617078aec56353be1a75f1c5ed814aa208dcae8d4bdefb9c5` |
| nginx root | `/var/www/marketplace-analytics` |
| Published at | 2026-07-20T17:26:59Z |

## Smoke

`scripts/post_deploy_smoke_test.sh` → **PASS** (systemd units, `/health`, auth, reports, costs, dashboard/summary, frontend `/`).

## F2 UI (HTTPS-served bundle)

All required markers present; forbidden legacy markers absent (Primary Answer, Trust Chip, Action Strip, Top SKU, F2 nav, F1.6 onboarding; no Hero KPI subtitle / Business Signals / Focus / sku_mapping / first_ai / walkthrough).

## Performance (post-deploy)

| Metric | Before (R1 / prior cert) | After R2 |
|--------|--------------------------|----------|
| Summary HTTPS (mvp user, 5 warmed) | ~1.7 s class (9.18-D1) | median ≈ **1.48 s** (samples 1.38–1.78 s) |
| Summary payload | slim (~8–13 KB class) | **8269** bytes (slim queues empty) |
| Main FE JS | `index-0fnrG7B4.js` 530.9 KB | `index-CfF3RxW0.js` 530.6 KB (F2; Recharts still deferred) |
| Index / asset TTFB | ~12–17 ms | ~8–14 ms |

Browser full-page TTI and upload E2E timing were not re-instrumented in R2; API/FE artifact evidence confirms accelerated summary path remains live and F2 hierarchy is served.

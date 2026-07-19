# Phase 9.17-F — Production Reconciliation & Release Certification

**Date:** 2026-07-19 (UTC)  
**Mode:** Audit + docs fix + certification  
**Certified runtime SHA:** `f85dea6151cc8b222b4aa794d72fac1939c5f1cd`  
**Docs reconciliation:** see git `main` tip after 9.17-F docs commits

## Identity matrix

| Component | Value |
|-----------|-------|
| Local HEAD | `f85dea6…` |
| `origin/main` | `f85dea6…` |
| `release/task0-jam-subscription-expenses` | `f85dea6…` |
| Production backend / worker cwd | same repo @ `f85dea6…` (restart 17:36 UTC) |
| Alembic | `0037_inv_stream_idx` |
| Frontend bundle | `index-DVVPbWvu.js` @ 2026-07-18 06:47 UTC |

**HEAD == MAIN == RELEASE == PRODUCTION (backend)** ✓  
**FE surface** unchanged since 9.16-C (bundle still current for seller dashboard).

## Git dirty-tree classification (pre-cert)

| Class | Items | Action |
|-------|-------|--------|
| **Temp / generated** | `.coverage`, `tmp_*`, `frontend/test-results/`, `reports_*.png`, `tsconfig.app.tsbuildinfo` | Leave untracked |
| **Secrets / local** | `.env.bak.int2` | Leave untracked |
| **Unwired WIP** | `profit-reconciliation-bridge*`, `test_sku_economics_decimal_coercion.py`, `phase_99a_*` | Leave untracked (not in product path) |
| **Historical screenshots** | `docs/release/screenshots/phase-*` | Optional evidence; not required for GO |
| **Release docs (this phase)** | README, CHANGELOG, 9.17-E1/F certs, hub indexes | **Committed** |

## AI policy (re-certified)

| Journey | Tokens |
|---------|--------|
| After upload | NO |
| After ETL (defaults) | NO (`post_report_ai_skipped_disabled`) |
| Open Dashboard / Analytics | NO |
| Open Recommendations / AI Assistant | NO on mount; YES only on «Запустить анализ» |

Live `.env`: `AI_AUTO_RECOMMEND_AFTER_REPORT=false`, `AI_ENABLED=true`.

## Deploy actions in 9.17-F

| Action | Required? | Result |
|--------|-----------|--------|
| Backend restart | No (already on `f85dea6`) | — |
| Worker restart | No | — |
| Frontend deploy | No (bundle already `DVVPbWvu`) | — |
| Docs commit + push | Yes | This certification |

## Final checklist

| # | Item | Status |
|---|------|--------|
| 1–4 | Commit / GitHub / Release / Backend SHA | `f85dea6…` |
| 5 | Frontend bundle | `DVVPbWvu` |
| 6 | Deploy timestamp (BE) | 2026-07-19 17:36 UTC |
| 7 | README | Aligned to 9.17-F |
| 8 | Documentation | Aligned; historical 9.16-C docs retained |
| 9 | AI policy | Explicit-only · certified |
| 10 | **GO / NO-GO** | **GO** |

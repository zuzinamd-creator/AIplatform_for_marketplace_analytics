# Phase 9.17-F — Production Reconciliation & Release Certification

**Date:** 2026-07-19 (UTC)  
**Mode:** Audit + docs fix + certification  
**Certified runtime SHA (ETL/AI deploy):** `f85dea6151cc8b222b4aa794d72fac1939c5f1cd`  
**Docs tip:** `main` / `release/task0-jam-subscription-expenses` (docs-only commits after runtime; `app/` unchanged)

## Identity matrix

| Component | Value |
|-----------|-------|
| Local HEAD / `origin/main` / release | aligned (`main` tip) |
| Production app code | `f85dea6…` (identical `app/` through docs tip) |
| Backend / worker restart | 2026-07-19 17:36:37 / 17:36:39 UTC |
| Alembic | `0037_inv_stream_idx` |
| Frontend bundle | `index-DVVPbWvu.js` @ 2026-07-18 06:47 UTC |
| Tag `certified-production` | points at docs tip (ops recovery assess) |

**HEAD == MAIN == RELEASE == PRODUCTION working tree** ✓  
**FE surface** unchanged since 9.16-C (bundle still current).

## Git dirty-tree classification

| Class | Items | Action |
|-------|-------|--------|
| **Temp / generated** | `.coverage`, `tmp_*`, `frontend/test-results/`, `reports_*.png`, `tsconfig.app.tsbuildinfo` | Leave untracked |
| **Secrets / local** | `.env.bak.int2` | Leave untracked |
| **Unwired WIP** | `profit-reconciliation-bridge*`, `test_sku_economics_decimal_coercion.py`, `phase_99a_*` | Leave untracked (not in product path; deploy-guard WARN) |
| **Historical screenshots** | `docs/release/screenshots/phase-*` | Optional evidence; untracked |
| **Release docs (this phase)** | README, CHANGELOG, 9.17-E1/F certs, hub indexes | **Committed + pushed** |

## AI policy (re-certified)

| Journey | Tokens |
|---------|--------|
| After upload | **NO** |
| After ETL (defaults) | **NO** (`post_report_ai_skipped_disabled`) |
| Open Dashboard / Analytics | **NO** |
| Open Recommendations / AI Assistant | **NO** on mount; **YES** only on «Запустить анализ» |

Live `.env`: `AI_AUTO_RECOMMEND_AFTER_REPORT=false`, `AI_ENABLED=true`.

Inventory: [phase_917b1_ai_inventory.md](phase_917b1_ai_inventory.md) · policy: [../product/ai_trigger_policy.md](../product/ai_trigger_policy.md)

## Deploy actions in 9.17-F

| Action | Required? | Result |
|--------|-----------|--------|
| Backend restart | No (already on `f85dea6` app code) | — |
| Worker restart | No | — |
| Frontend deploy | No (bundle already `DVVPbWvu`) | — |
| Docs commit + push + release FF | Yes | Done |
| `certified-production` tag | Moved to docs tip for recovery assess | Done |

## Final checklist

| # | Item | Status |
|---|------|--------|
| 1 | Commit SHA (docs tip) | `main` tip |
| 2 | GitHub SHA | = `main` tip |
| 3 | Release SHA | = `main` tip |
| 4 | Backend runtime SHA | `f85dea6…` (`app/` unchanged since) |
| 5 | Frontend bundle | `DVVPbWvu` |
| 6 | Deploy timestamp (BE) | 2026-07-19 17:36 UTC |
| 7 | README | Aligned to 9.17-F |
| 8 | Documentation | Aligned; historical 9.16-C FE docs retained |
| 9 | AI policy | Explicit-only · certified |
| 10 | **GO / NO-GO** | **GO** |

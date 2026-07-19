# Phase 9.17-G — Runtime Alignment Certification

**Date:** 2026-07-19 (UTC)  
**Mode:** Audit + alignment + certification  
**Goal:** `HEAD = MAIN = RELEASE = BACKEND = FRONTEND = PRODUCTION`

## STEP 1 — Why HEAD was `ac26b8c` while “runtime” looked like `f85dea6`

| Fact | Explanation |
|------|-------------|
| Git tip after 9.17-F | Docs-only commits on top of ETL deploy `f85dea6` |
| `git diff f85dea6..HEAD -- app/` | **Empty** — no Python/runtime code change |
| `git diff f85dea6..HEAD -- frontend/src/` | **Empty** — no seller UI source change |
| Backend/worker PIDs | Started **2026-07-19 17:36 UTC** at the ETL deploy moment (`f85dea6`) |
| Working directory | Always the same repo checkout (processes load modules from disk) |

**Was that acceptable?**  
**Yes for correctness** (identical `app/` and `frontend/src`), but **not** for release identity. Operators and recovery assess need process start + FE publish to match the certified tip. Phase 9.17-G closes that identity gap.

## STEP 2 — Backend alignment

| Action | Result |
|--------|--------|
| `systemctl restart marketplace-backend marketplace-worker` | **Done** |
| Runtime stamp | `/var/lib/marketplace-analytics/runtime_sha` = HEAD |
| Health | `/health` OK |

After the final docs tip commit of this phase, services are restarted once more so **runtime SHA = HEAD**.

## STEP 3 — Frontend alignment

| Check | Result |
|-------|--------|
| Source vs bundle origin `7f65cfb` | Unchanged through HEAD |
| Rebuild + publish | **Done** (2026-07-19 23:04 UTC) |
| Bundle hash | **`index-DVVPbWvu.js`** (unchanged hash = content-identical rebuild) |
| Stamp | `/var/lib/marketplace-analytics/frontend_deploy_sha` = HEAD |

Bundle hash staying `DVVPbWvu` is expected and correct: Vite content hash is stable when `frontend/src` is unchanged.

## STEP 4 — Identity matrix

| Component | Value |
|-----------|-------|
| HEAD / main / release / `certified-production` | See final report (tip after this doc commit) |
| Backend runtime SHA | = HEAD (stamp + restart) |
| Frontend deploy SHA | = HEAD |
| Frontend bundle | `index-DVVPbWvu.js` |
| Alembic | `0037_inv_stream_idx` |

## STEP 5 — Readiness for Phase 9.18

### A. Dashboard Performance Audit — known bottlenecks

| Area | Evidence / note |
|------|-----------------|
| **Dashboard summary API fan-out** | Single `/dashboard/summary` aggregates finance, trends, top SKUs, AI ops embeds — watch TTFB on pilot tenant |
| **Remote DB RTT (VPS ↔ Supabase)** | Same class of cost as ETL; many sequential queries amplify latency |
| **Large JS bundle** | `index-DVVPbWvu.js` ~1.07 MB / ~300 KB gzip — code-split candidates for 9.18 |
| **Charts / Insight Engine V1** | Deterministic FE captions (no LLM) — still client CPU on dense periods |
| **Upload → dashboard wait** | Post–9.17-E inventory much faster; **Phase 3 aggregates** still a candidate for large dense windows (Job B historically) |
| **Cold vs warm caches** | Re-upload of same window understates Phase 3 cost — audit must use cold/comparable windows |

### B. Premium UI Audit — seller notes & design scope

| Seller / product note | Source |
|----------------------|--------|
| Top SKU truncation / readability | Fixed in 9.14; re-verify on mobile |
| Cost structure + daily total costs clarity | 9.15–9.16 |
| Margin label confusion (three margins) | Documented in `margin_semantics.md` — UI still needs premium clarity |
| Insight Engine captions may overlap Business Signals (cost share) | Noted in 9.16-C baseline follow-up |
| Long ETL wait UX honesty | 9.17-B UX audit — progress copy |
| Auto-AI off | Sellers must use «Запустить анализ» — onboarding clarity |
| Trust banners / COGS gating | Partial/insufficient states still need premium empty states |

**Design audit areas:** hero KPI hierarchy, chart caption density, mobile Overview, Financial Summary flat «Расходы WB», Top SKU attention states, trust badges, AI entry points without implying auto-run.

## Verdict

**GO** — runtime identity aligned; ready for 9.18 audits (no product logic change in G).

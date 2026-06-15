# Production Testing Baseline — Phase 6.8.2 MVP

**Date:** 2026-06-16  
**Release:** 6.8.2 MVP (Driver Cards + Period Decision)  
**Host:** https://321997.fornex.cloud  
**Pilot user:** `margarita.zuzina@mail.ru` (`caefecb3-5789-4878-a9d4-929be573fbcc`)  
**Status:** RELEASE CANDIDATE READY

This document is the frozen baseline for user testing. All subsequent improvements should be measured against this snapshot.

---

## 1. Release Snapshot

| Component | Value |
|-----------|-------|
| **Backend commit** | `8f78721cf68a5859a748bddbcc5b0a92f6beb7ef` (`8f78721`) — *fix(ai): replace dashboard fallback in summary when period decision exists* |
| **Backend deployed from** | `/root/AIplatform_for_marketplace_analytics` |
| **Backend service** | `marketplace-backend` (uvicorn :8000) |
| **Frontend git base** | `2e708c195dc9dd74ea0d430d5a9a4e8793400c39` (`2e708c1`) — *feat(ai): add 6.8.2 MVP driver cards and period decision* |
| **Frontend deployed state** | Working tree **with uncommitted fix** in `RecommendationDetailPage.tsx` (Decision Block uses `period_decision.action` for `single`/`alternative`) |
| **Bundle hash** | `index-C8DaJeNO.js` |
| **Bundle CSS** | `index-B7aQDnJw.css` |
| **Build / deploy time** | 2026-06-15 22:40 UTC |
| **Deploy path** | `/var/www/marketplace-analytics/` |
| **Deploy script** | `scripts/deploy-frontend.sh` |
| **driver_engine_version** | `6.8.2-mvp` |

### Git divergence (record only)

- Branch `main` is **ahead of `origin/main` by 2 commits** (`2e708c1`, `8f78721`).
- Frontend Decision Block fix is **deployed to production but not committed** (8 lines in `RecommendationDetailPage.tsx`).

---

## 2. Known Issues

### BLOCKER

*None.* Core pilot flows (Single Decision, Data First, Driver Cards) are verified on production.

### NON-BLOCKER

| # | Issue | Screen | Impact on testing | Notes |
|---|-------|--------|-------------------|-------|
| 1 | `GET /api/v1/ai/recommendations/stats` returns **422** — route `/stats` captured by `/{recommendation_id}` | Recommendation list | **No** — list loads, items open; stats widget empty | Pre-existing routing order in `app/api/ai.py` |
| 2 | Data First copy says «Включите сравнение…» when compare period has **zero sales** | Recommendation detail (Data First) | **Low** — mode and action still correct; wording may confuse pilot user | Compare empty ≠ comparison disabled |
| 3 | `pickSellerAction()` regex `\b` fails on Cyrillic — Dashboard fallback on non-`single`/`alternative`/`data_first` paths | Recommendation detail | **No** for pilot scenarios | Fixed path deployed for `single`/`alternative`/`data_first` |
| 4 | Default pilot periods (Jan–Mar compare) yield **Data First**, not Single Decision | Recommendation detail | **No** if using baseline IDs below | First sale 2026-05-11; use in-May compare windows |
| 5 | `split_fallback` does not propagate `compare_available` | Backend logic | **No** for baseline scenarios | Future edge-case only |
| 6 | Long analytics text in «Что произошло» | Recommendation detail | **No** — readability only | |
| 7 | Frontend fix deployed but **uncommitted** in git | Release reproducibility | **No** for current test; **yes** for next deploy from clean checkout | Commit before next release |
| 8 | `main` not pushed to `origin` | Git / CI | **No** for on-server pilot | Remote is 2 commits behind server |

---

## 3. Testing Baseline

Validated on production 2026-06-16. Bundle `index-C8DaJeNO.js`.

### 3.1 Single Decision

| Field | Value |
|-------|-------|
| **recommendation_id** | `b164b783-9f91-4967-bdf5-9d8ca663aef4` |
| **URL** | `/app/ai/recommendations/b164b783-9f91-4967-bdf5-9d8ca663aef4` |
| **Periods** | current: 2026-05-16 … 2026-05-31, compare: 2026-05-01 … 2026-05-15 |
| **Expected API** | `period_decision.mode = "single"` |
| **Expected UI label** | СДЕЛАЙТЕ СЕГОДНЯ |
| **Expected action** | Обновите карточку SKU j-31-239: фото, размеры и описание комплектации. |

### 3.2 Data First

| Field | Value |
|-------|-------|
| **recommendation_id** | `02bf93a2-4883-4d80-a77c-481467c0a501` |
| **URL** | `/app/ai/recommendations/02bf93a2-4883-4d80-a77c-481467c0a501` |
| **Periods** | current: 2026-03-12 … 2026-03-31, compare: 2026-01-01 … 2026-03-11 |
| **Expected API** | `period_decision.mode = "data_first"`, `blocked_reason = "no_compare"` |
| **Expected UI label** | СНАЧАЛА ДАННЫЕ |
| **Expected action** | Включите сравнение с предыдущим периодом — без него нельзя выбрать главный SKU-драйвер. |

### 3.3 Driver Cards

Use **either** baseline recommendation above.

| Check | Expected |
|-------|----------|
| Count | 3 cards |
| Accordion | «Драйверы (3)» expands |
| SKUs | j-31-239 (rank 1), j-22-004 (rank 2), j-22-027 (rank 3) |
| Per card | Причина, Действие, Эффект visible after expand |

### 3.4 Recommendation List

| Check | Expected |
|-------|----------|
| List loads | Yes |
| Items open detail | Yes |
| Console on detail pages | No React errors, no JS exceptions |
| Console on list page | 2× 422 on `/ai/recommendations/stats` (non-blocking) |

---

## 4. Rollback Info (do not execute)

### Current RC (frozen)

| Layer | Rollback target |
|-------|-----------------|
| Backend commit | `8f78721` |
| Frontend bundle | `index-C8DaJeNO.js` |
| Frontend path | `/var/www/marketplace-analytics/` |

### Roll back backend to pre-6.8.2

```bash
cd /root/AIplatform_for_marketplace_analytics
git checkout 0341bfc   # last commit before 6.8.2 MVP
sudo systemctl restart marketplace-backend
```

Intermediate: `2e708c1` (6.8.2 without summary dashboard fix).

### Roll back frontend

**Option A — DR backup (pre-RC, pre-Decision-Block-fix):**

```bash
tar -xzf /root/backups/marketplace-drill/frontend-static-20260614T030210Z.tar.gz -C /var/www/
# Bundle in backup: index-KajBAyHo.js
```

**Option B — rebuild from git (no uncommitted fix):**

```bash
cd /root/AIplatform_for_marketplace_analytics
git checkout 2e708c1 -- frontend/   # or full checkout at 2e708c1
bash scripts/deploy-frontend.sh
```

**Option C — rebuild buggy bundle (had Dashboard fallback in Decision Block):**

Requires source tree at `2e708c1` without the `RecommendationDetailPage.tsx` fix; previous bundle `index-B4ZqizaR.js` was removed by `rsync --delete` on 2026-06-15 deploy.

### Deployment paths reference

| Resource | Path |
|----------|------|
| App repo | `/root/AIplatform_for_marketplace_analytics` |
| Frontend static | `/var/www/marketplace-analytics/` |
| Backend unit | `/etc/systemd/system/marketplace-backend.service` |
| DR frontend backups | `/root/backups/marketplace-drill/frontend-static-*.tar.gz` |

---

## 5. Release Status

**RELEASE CANDIDATE READY**

Pre-pilot validation passed for Single Decision, Data First, and Driver Cards on production with bundle `index-C8DaJeNO.js` and `driver_engine_version: 6.8.2-mvp`.

### Residual risks (not blockers)

1. Stats widget 422 on list page.
2. Data First wording when compare period is empty.
3. Uncommitted frontend fix — reproducibility gap until committed and pushed.
4. Pilot must use baseline recommendation IDs and periods; default Jan–Mar run will not show Single Decision.

---

## 6. API quick-check

```bash
# From server with pilot JWT
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://321997.fornex.cloud/api/v1/ai/recommendations/b164b783-9f91-4967-bdf5-9d8ca663aef4" \
  | jq '.action_plan.period_decision.mode, .action_plan.driver_cards | length, .action_plan.driver_engine_version'
```

Expected: `"single"`, `3`, `"6.8.2-mvp"`.

---

*Baseline frozen. No further changes until user testing feedback.*

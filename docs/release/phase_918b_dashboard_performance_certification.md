# Phase 9.18-B — Dashboard Performance Optimization

**Date:** 2026-07-20 (UTC)  
**Mode:** Audit → P0 implementation → tests → production certification  
**Scope:** Accelerate Dashboard first paint. **No Premium UI** (deferred to 9.18-C).

Pilot tenant: `caefecb3-5789-4878-a9d4-929be573fbcc` (`platform_admin`)  
Period: `2026-07-06` … `2026-07-12` · marketplace `wildberries`  
Endpoint: `GET /api/v1/dashboard/summary`

---

## STEP 1 — Performance baseline (production, pre-change)

### Open-path fan-out (pre-9.18-B)

| Branch | Approx. parallel cost (local DB) | First-screen critical? | Notes |
|--------|----------------------------------|------------------------|-------|
| `finance_summary` | ~1.5–1.7 s | **Yes** | KPI card + cost structure |
| `cost_coverage` (limit=20) | ~1.3–1.7 s | **Yes** (aggregates only) | Per-SKU rows unused on dashboard |
| `coverage` | ~1.0–1.7 s | Secondary | Top SKU footer dates |
| `finance_trend` | ~0.8–1.4 s | **Yes** | Cost structure chart |
| `queue` (10 jobs) | ~0.5–0.6 s | Admin KPI counts only | Job rows unused |
| `runtime` | ~0.5–0.7 s | Admin rebuild KPI | Also polled by TrustBanners |
| `ai_ops` | ~0.5–0.6 s | Admin mode flag | Duplicate of TrustBanners poll |
| `todays_focus` | ~0.3–0.6 s | `dangerous` only | **priority_queue ~306 KB** unused |
| `recommendations` (5 full) | ~0.3–0.6 s | Admin **count** only | **items ~182 KB** unused |
| `revenue_*` / `top_skus` | ~0.1–0.3 s | **Yes** | Core KPIs / Top SKU |

Pre-change: **12** parallel `SessionLocal()` connections per summary (admin).

### Measured BEFORE (HTTPS production, 5 samples, warmed)

| Metric | Value |
|--------|-------|
| Summary latency median | **6850.5 ms** |
| Summary latency mean | **6866.1 ms** |
| TTFB (httpx `elapsed` ≈ headers) median | **6847.8 ms** |
| Payload size | **513 668 bytes** |

---

## STEP 2 — Payload audit

| Key | Bytes (JSON) | Used on Dashboard FE? | Decision |
|-----|--------------|----------------------|----------|
| `todays_focus` | ~307 626 | Only `dangerous[:3]` | Drop `priority_queue` + unused lists |
| `recommendations` | ~182 050 | Only count | `items=[]`, `page.total` |
| `cost_coverage` | ~7 807 | Trust aggregates + missing sample | `items=[]`, cap missing ≤20 |
| `queue` | ~4 234 | `status_counts` (admin) | `items=[]`, `limit=0` |
| Trends / KPIs / top_skus | ~10 k combined | **Yes** | Keep |
| `runtime` / `ai_ops` | <1 k | Admin KPIs | Keep for admin; stubs for seller |

| | Bytes | Reduction |
|--|-------|-----------|
| **Current payload** | 513 668 | — |
| **Required payload** (first screen) | ~11–16 k | — |
| **Potential reduction** | | **~97%** |

Local new-code serialize check: **15 522 bytes** (−97.0%).

---

## STEP 3 — Frontend performance audit

| Asset / area | Pre-9.18-B | P0 action |
|--------------|------------|-----------|
| Main JS bundle | Single chunk `index-DVVPbWvu.js` ~1044 KB / ~292 KB gzip | Split Recharts via `manualChunks` + lazy panels |
| Recharts | Eager in `DashboardPage` | `DeferredCharts` lazy load |
| Top SKU | In summary + optional sort fetch | Unchanged (already deferred sort) |
| AI / Business Signals / Trust | Summary embeds + shell polls | Slim embeds; TrustBanners unchanged |
| Premium visual redesign | N/A | **Not in 9.18-B** |

---

## STEP 4 — Roadmap

| Pri | Item | Expected gain | Risk | Effort |
|-----|------|---------------|------|--------|
| **P0** | Slim summary payload + admin-gated ops fan-out + cost `limit=0` + rec count-only | −90%+ payload; −1–3 s latency | Low (schema-compatible empties) | S |
| **P0** | Lazy Recharts / cost panel + Vite chunk | Smaller first JS parse | Low | S |
| **P1** | Cache revenue/finance summary TTL; SQL tune finance/coverage | −0.5–1.5 s | Med | M |
| **P1** | Dedicated `/dashboard/focus-lite` without loading 30 rec rows | −0.3–0.5 s | Low | S |
| **P2** | HTTP cache / ETag; secondary hydrate endpoint | UX polish | Med | M |
| **9.18-C** | Premium UI | Visual only | — | — |

---

## STEP 5 — Implementation (P0 only)

### Backend
- `DashboardService.summary`: sellers → **8** DB sessions; admins → **12** but lighter queries.
- Empty `todays_focus.priority_queue`, empty `recommendations.items` + `page.total`, empty `queue.items`.
- `CostCoverageService.analyze(..., limit=0)`; cap `missing_skus` to 20.
- `AIService.count_recommendations()` for admin KPI.

### Frontend
- Rec count from `recommendations.page.total`.
- `DeferredCharts.tsx` + Vite `recharts` manual chunk.

### Tests
- `tests/unit/test_dashboard_summary_slim.py`
- `DashboardPage.test.tsx` updated

---

## STEP 6 — Performance certification (production AFTER)

Measured 2026-07-19 ~23:25 UTC · same pilot/period · HTTPS `321997.fornex.cloud` · 5 warmed samples.

| Metric | BEFORE | AFTER | Gain |
|--------|--------|-------|------|
| Summary latency median | **6850.5 ms** | **4161.3 ms** | **−2689 ms (−39.3%)** |
| Summary latency mean | 6866.1 ms | 4133.9 ms | −2732 ms |
| Payload bytes | **513 668** | **13 335** | **−500 333 (−97.4%)** |
| TTFB median (httpx `elapsed`) | **6847.8 ms** | **4156.2 ms** | **−2692 ms** |

Sanity (AFTER): `priority_queue=[]`, `recommendations.items=[]` / `page.total=39`, `cost_coverage.items=[]`, `queue.items=[]`.

### Frontend bundle (production publish)

| Chunk | Size | gzip |
|-------|------|------|
| `index-0fnrG7B4.js` (main) | 530.9 KB | 145.5 KB |
| `recharts-DlIxri3H.js` | 530.5 KB | 153.1 KB |
| `CostStructurePanel-ttn12Bn0.js` | 7.4 KB | 2.7 KB |

Previous single chunk: `index-DVVPbWvu.js` ~1044 KB / ~292 KB gzip. Main first-load JS roughly **halved** (Recharts deferred).

---

## STEP 7 — Release identity

| Pointer | SHA / value |
|---------|-------------|
| **Code (P0 impl)** | `094646adb058f5c5ff901e7cbba2c341208e3a63` |
| **Certification seal (AFTER metrics)** | `d64db8572c1ed0e9811de2e8cd6990ceaf9cbc2e` |
| **Identity tip** | Must match `HEAD` = `origin/main` = `release/*` = `certified-production` = runtime/FE stamps. **Do not pin tip inside this cell** (docs commits would self-desync). Operators: `git rev-parse HEAD` and `cat /var/lib/marketplace-analytics/runtime_sha`. |
| FE bundle | `index-0fnrG7B4.js` (+ deferred `recharts-DlIxri3H.js`) |

`git diff 094646a..HEAD -- app/ frontend/src/` → **empty** after the P0 code commit (subsequent commits are docs-only).


---

## STEP 8 — Verdict

**GO**

Root causes confirmed and fixed on P0 path; production measurements show material latency and payload wins without Premium UI.

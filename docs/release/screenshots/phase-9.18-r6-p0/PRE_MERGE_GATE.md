# Phase 9.18-R6-P0 — pre-merge gate report (WCAG + chart QA)

**Date:** 2026-07-20 · **Prod:** untouched (`index-Df_toJsq.js`)  
**Staging:** https://321997.fornex.cloud:8443/ · bundle `index-D3zN5m_C.js`

## WCAG fixes applied

| Pair | Before | After | Ratio |
|------|--------|-------|------:|
| light warn / warnSoft | `#B86E00` / `#FFF6E5` = 3.71 FAIL | `#9A5A00` / `#FFF6E5` | **5.10 PASS** |
| dark action / actionSoft | `#3B8DD9` / `#0F2A45` = 4.17 FAIL | `#3B8DD9` / `#0A1F35` | **4.76 PASS** |

Unit tests: `design-tokens.test.ts` — **36 tests** covering ink/panel/canvas, large metrics, **all soft pairs**, light **and** dark.

## P1 (not P0) — fold

Desktop PA ≈ **599px** (staging 1440×900).  
**Problem:** чек-лист «Первый запуск» + period selector съедают fold. Chrome diet helped (~845→599) but does not close executive fold. Next phase.

## Chart QA evidence

Live MVP account: sparse/empty chart series in UI for cost & SKU lines (trust/costs gap).  
Confirmed no purple via staging JS forensics + palette board:

`docs/release/screenshots/phase-9.18-r6-p0/chart-qa/`

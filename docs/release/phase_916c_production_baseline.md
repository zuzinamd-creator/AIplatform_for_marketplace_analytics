# Phase 9.16-C — Production baseline certification

**Status:** CERTIFIED · **GO**  
**Date:** 2026-07-18

## Baseline

| Field | Value |
|-------|-------|
| Commit / GitHub / Release SHA | `7f65cfb015dda2cc869afd3e16fa0e94b95d72a9` |
| Frontend bundle | `index-DVVPbWvu.js` (`DVVPbWvu`) |
| Previous FE bundle | `index-BUMXPZet.js` (Phase 9.15) |
| Backend SHA | `7f65cfb` (same repo; FE-only code change, no backend restart) |
| Deploy timestamp | 2026-07-18 06:47:19 UTC |
| Host | `321997.fornex.cloud` |

## What shipped (seller-facing)

1. **Insight Engine V1** — FACT + DRIVER + ATTENTION on four dashboard charts  
2. **Margin semantics** — Маржа по выплате / Маржа SKU / Маржа (юнит-экономика) + hints  
3. **Financial Summary** — flat «Расходы WB»; removed «Детализация услуг WB» accordion  
4. **Daily costs clarity** — total-cost formula subtitle, period share strip, share notes  

## Constraints

- No backend profit formula changes  
- No AI-generated chart captions  
- FE-first deterministic logic only  

## Related phases

| Phase | Commit (approx) | Bundle | Notes |
|-------|-----------------|--------|-------|
| 9.14-B | `8b04dff` | `CvvSRyh3` | Top SKU readability, cost structure panel |
| 9.15-B | `0579f09` | `BUMXPZet` | Commission row, daily total costs, early captions |
| 9.16-C | `7f65cfb` | `DVVPbWvu` | Insight Engine V1 + margin labels + FS flatten |

## Docs reconciliation

Phase **9.16-D** updates README and product/frontend/release docs to this baseline.

## Known residual (C1)

Cost share % may still appear in both Business Signals and cost-structure insight. Track for a follow-up de-dup if sellers report noise.

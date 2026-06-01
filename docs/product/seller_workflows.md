# Seller workflows (UX-2)

This doc formalizes the intended “real seller” workflows and where they live in the product UI.

## Daily routine (5–10 min)

1. **Upload report** (if new data)
   - `/app/reports/upload`
2. **Confirm processing**
   - `/app/reports`
   - `/app/ops/queue`
3. **Review anomalies**
   - `/app/ops/anomalies`
4. **Review AI recommendations**
   - `/app/ai/recommendations`
   - Accept/reject with rating + rationale

## Weekly analysis workflow (30–60 min)

Goal: compare periods, profitability review, inventory analysis, operational risks.

UX-2 status:

- Ops + AI visibility is implemented.
- KPI comparison (revenue/profit/margin/top SKUs/trends) is **blocked** until metrics read endpoints exist.

## Problem investigation workflow

Trigger: seller sees missing data, staleness, anomalies, or unexpected results.

1. Check queue status: `/app/ops/queue`
2. Check rebuild lifecycle: `/app/ops/rebuilds`
3. Check drift checks: `/app/ops/drift-checks`
4. Check anomalies: `/app/ops/anomalies`
5. Review report lifecycle: `/app/reports/:reportId`
6. Use AI explainability (when applicable): `/app/ai/recommendations/:id`

## AI-assisted decision workflow

1. Open recommendation detail
2. Read “Why this matters” + suggested action
3. Review explainability
4. Record usefulness rating + accept/reject rationale


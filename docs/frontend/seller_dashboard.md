# Seller financial dashboard (Analytics Overview)

**Production baseline:** platform post–**9.18-B** (slim dashboard summary) · dashboard surface Phase **9.16-C** (Insight Engine V1)  
**Release cert:** [phase_918b_dashboard_performance_certification.md](../release/phase_918b_dashboard_performance_certification.md)

Primary seller overview lives under **Analytics Hub** (`/app/analytics`, Overview tab).  
Legacy route `/app/dashboard` soft-redirects to the hub (Phase 9.8-B).

### Performance note (9.18-B)

`GET /dashboard/summary` is optimized for first paint: AI priority queues and full recommendation bodies are **not** embedded (use AI pages). Charts (Recharts) load via deferred chunks.

## Goals

- Period-aware KPI summary with trust gating
- Charts that explain **what / why / attention** (Insight Engine V1)
- Clear margin semantics (three different metrics, distinct labels)
- Cost structure and daily total costs without tooltip-only explanations
- Business Signals for high-priority alerts
- Completeness / integrity / freshness warnings

## Layout (seller-visible)

1. **Hero KPI** — sales revenue · net profit · **Маржа по выплате** · profitability  
2. **Business Signals** — up to 3 deterministic alerts (cost share, returns, weak SKU)  
3. **Выручка и прибыль по дням** + Insight Engine caption  
4. **Топ SKU** — revenue / profit / **Маржа SKU** tabs + contribution insight  
5. **Структура расходов за период** — horizontal bars + legend (₽ and %) + share note  
6. **Общие затраты по дням** — total-cost bars + period share strip + share note  
7. **Финансовая сводка** — flat **Расходы WB** block (no services accordion)

## Margin labels (do not conflate)

| UI label | Surface | Formula (unchanged) |
|----------|---------|---------------------|
| **Маржа по выплате** | Hero + Financial Summary | `(total_to_pay − COGS) / revenue × 100` |
| **Маржа SKU** | Top SKU | `Σ net_profit / Σ revenue × 100` (`sku_daily_metrics`) |
| **Маржа (юнит-экономика)** | Economics table / drilldown | `contribution_margin / revenue × 100` |

Static `i` hints explain each formula. See [margin_semantics.md](../product/margin_semantics.md).

## Financial Summary — «Деньги от Wildberries»

Order (Phase 9.16-C):

1. Выручка  
2. К перечислению за товар  
3. **Расходы WB** (flat group): Комиссия WB → Логистика → Хранение → Удержания WB  
4. Выплата от WB  
5. Себестоимость → Чистая прибыль → **Маржа по выплате**

Accordion allowed only for **Из них** (promotion / jam under удержания) and **Ещё показатели** (рентабельность).

## Cost charts

| Chart | Includes returns? | What seller sees |
|-------|-------------------|------------------|
| Структура расходов за период | Yes (separate slice when present) | Category ₽ + % of period expense total |
| Общие затраты по дням | **No** (product rule) | Sum of commission + logistics + ads + storage + penalties + deductions + acquiring + other |

Share note on both: `% — доля от общей суммы расходов за период`.

Daily chart shows a **single total** series; period composition strip under the chart makes categories visible without hover. Day-level breakdown remains in tooltip as secondary detail.

## Business Signals vs chart insights

| Layer | Role |
|-------|------|
| **Business Signals** | Short alerts at top (e.g. «Комиссия WB составляет N%…») |
| **Chart insights** | Per-chart FACT + DRIVER + ATTENTION (Insight Engine V1) |

Known residual: cost **share %** can still appear in both layers (C1 audit). Prefer different wording; do not delete Signal without product decision.

## Insight Engine V1

Deterministic FE captions — no LLM. Spec: [dashboard_insight_engine.md](../product/dashboard_insight_engine.md).

## Implementation map

| Area | Files |
|------|-------|
| Page | `frontend/src/views/dashboard/DashboardPage.tsx` |
| Insights | `frontend/src/views/dashboard/chart-insights.ts` |
| Costs UI | `frontend/src/views/dashboard/CostStructurePanel.tsx`, `cost-structure-chart.ts` |
| Financial Summary | `frontend/src/views/dashboard/FinancialSummaryCard.tsx` |
| Top SKU | `frontend/src/views/dashboard/TopSkusCard.tsx` |
| Signals | `frontend/src/views/dashboard/business-signals.ts` |
| Margin labels | `frontend/src/views/dashboard/margin-labels.ts` |
| Trust | `frontend/src/state/profit-trust.ts` |

## Related

- [dashboard_insight_engine.md](../product/dashboard_insight_engine.md)
- [margin_semantics.md](../product/margin_semantics.md)
- [financial_semantics.md](../analytics/financial_semantics.md)
- [phase_916c_production_baseline.md](../release/phase_916c_production_baseline.md)
- [frontend-deploy.md](../ops/frontend-deploy.md)

# Seller financial dashboard (Analytics Overview)

**Production baseline:** Phase **9.18-F2** (Primary Answer + Action Strip + Trust Chip) · perf lineage **9.18-B** / **9.18-D1**  
**Release:** Phase **9.18-R2** production sync · bundle `index-CfF3RxW0.js`  
**Onboarding:** [onboarding.md](../product/onboarding.md) (F1.6)

Primary seller overview lives under **Обзор** (`/app/analytics`).  
Legacy route `/app/dashboard` soft-redirects here.

### Performance note (9.18-B / 9.18-D1)

`GET /dashboard/summary` is optimized for first paint: AI priority queues and full recommendation bodies are **not** embedded (use AI pages). Charts (Recharts) load via deferred chunks. Production HTTPS summary median remains in the **~1.4–1.8 s** class after 9.18-D1 (tenant/session cache).

## Goals

- One primary period answer (revenue / profit) with trust on the same surface
- Compact Action Strip for next seller moves
- Charts that explain **what / why / attention** (Insight Engine V1)
- Clear margin semantics (three different metrics, distinct labels)
- Cost structure and daily total costs without tooltip-only explanations
- Completeness / integrity / freshness warnings (no duplicate global trust banner on overview when Trust Chip is shown)

## Layout (seller-visible) — F2

1. **Period selector**  
2. **Primary Answer** — sales revenue · net profit · **Trust Chip**  
3. **Action Strip** — up to a few deterministic next actions (built from former Business Signals + focus cues)  
4. **Топ SKU** — revenue / profit / **Маржа SKU** tabs + contribution insight  
5. **Выручка и прибыль по дням** + Insight Engine caption (deferred Recharts)  
6. **Структура расходов за период** — horizontal bars + legend (₽ and %) + share note  
7. **Общие затраты по дням** — total-cost bars + period share strip + share note  
8. **Финансовая сводка** — flat **Расходы WB** block (no services accordion)

### Removed from overview (do not restore without product decision)

- Hero KPI grid (multi-card revenue / margin / profitability strip)
- Business Signals panel
- Focus section («Что требует внимания сегодня»)

## Navigation (F2 seller IA)

| Section | Role |
|---------|------|
| **Обзор** | Dashboard / Сегодня |
| **Аналитика** | Period compare, SKU economics, inventory, reconciliation |
| **Данные** | Upload, reports, costs, cost coverage |
| **Действия** | AI recommendations / digest |
| **Аккаунт** | Onboarding, settings, support |

## Margin labels (do not conflate)

| UI label | Surface | Formula (unchanged) |
|----------|---------|---------------------|
| **Маржа по выплате** | Financial Summary (and related trust surfaces) | `(total_to_pay − COGS) / revenue × 100` |
| **Маржа SKU** | Top SKU | `Σ net_profit / Σ revenue × 100` (`sku_daily_metrics`) |
| **Маржа (юнит-экономика)** | Economics table / drilldown | `contribution_margin / revenue × 100` |

Static `i` hints explain each formula. See [margin_semantics.md](../product/margin_semantics.md).

## Financial Summary — «Деньги от Wildberries»

Order (Phase 9.16-C, unchanged by F2):

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

## Action Strip vs chart insights

| Layer | Role |
|-------|------|
| **Action Strip** | Compact next actions on overview (replaces Business Signals panel + Focus) |
| **Chart insights** | Per-chart FACT + DRIVER + ATTENTION (Insight Engine V1) |

Signal builders may still live in `business-signals.ts` as input to Action Strip cards — the **panel UI is not shown**.

## Insight Engine V1

Deterministic FE captions — no LLM. Spec: [dashboard_insight_engine.md](../product/dashboard_insight_engine.md).

## Implementation map

| Area | Files |
|------|-------|
| Page | `frontend/src/views/dashboard/DashboardPage.tsx` |
| Primary Answer | `frontend/src/views/dashboard/PrimaryAnswer.tsx` |
| Action Strip | `frontend/src/views/dashboard/ActionStrip.tsx`, `action-strip.ts` |
| Trust Chip | `frontend/src/ui/trust-chip.tsx` |
| Insights | `frontend/src/views/dashboard/chart-insights.ts` |
| Costs UI | `frontend/src/views/dashboard/CostStructurePanel.tsx`, `cost-structure-chart.ts` |
| Financial Summary | `frontend/src/views/dashboard/FinancialSummaryCard.tsx` |
| Top SKU | `frontend/src/views/dashboard/TopSkusCard.tsx` |
| Signal builders (Action Strip input) | `frontend/src/views/dashboard/business-signals.ts` |
| Margin labels | `frontend/src/views/dashboard/margin-labels.ts` |
| Trust | `frontend/src/state/profit-trust.ts` |
| Nav IA | `frontend/src/shell/nav.ts` |

## Related

- [onboarding.md](../product/onboarding.md)
- [dashboard_insight_engine.md](../product/dashboard_insight_engine.md)
- [margin_semantics.md](../product/margin_semantics.md)
- [financial_semantics.md](../analytics/financial_semantics.md)
- [phase_918b_dashboard_performance_certification.md](../release/phase_918b_dashboard_performance_certification.md)
- [frontend-deploy.md](../ops/frontend-deploy.md)

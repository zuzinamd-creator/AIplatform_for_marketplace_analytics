# Dashboard Insight Engine V1 (Phase 9.16-C)

**Status:** Production (`7f65cfb`, bundle `DVVPbWvu`)  
**Location:** `frontend/src/views/dashboard/chart-insights.ts`  
**Mode:** Deterministic frontend only — **no AI / no LLM**

## Purpose

Replace chart narration («пик был DD.MM») with seller-useful captions that answer:

1. **What happened?** (Fact)  
2. **Why?** (Driver)  
3. **Does it need attention?** (Attention)

## Scope (four charts)

| Chart | Function | Primary inputs |
|-------|----------|----------------|
| Выручка и прибыль | `revenueProfitInsight` | `revenue_trend_daily` + optional `finance_trend_daily` |
| Структура расходов | `costStructureInsight` | Period composition from `finance_summary` KPIs |
| Общие затраты по дням | `costDynamicsInsight` | Daily total-cost rows (returns excluded) |
| Топ SKU | `topSkuInsight` | Leader `contribution_pct` |

## Deterministic rules

### Revenue / profit

- Compare each day to the **period average** of profit (if trust allows) or revenue.
- Focus day = largest **relative drop** below average (≥ 15% watch, ≥ 30% alert).
- **Driver:** cost category with largest increase vs its period average on that day, or revenue drop if larger.
- Attention strings: «Стоит проверить этот день.» / «Имеет смысл обратить внимание.»
- If no material drop: report upside vs average, or «без резких отклонений».

### Cost structure (period)

- Leader category by share of period expense total.
- Fact includes share % + «крупнейшая статья».
- Attention scales with concentration (≥ 40% / ≥ 55%).

### Daily total costs

- Peak day vs period average of daily totals.
- If one category ≥ 80% of that day → «почти все расходы дня составила {статья} (N%).»
- Else spike wording («в 2 раза выше среднего») + dominant category.

### Top SKU

- Fact: leader contribution %.
- Attention: ≥ 40% → business dependency; 25–40% → watch; else «в норме».

## Limitations

- Uses **intra-period** averages only (not WoW / prior period) in V1.
- Driver quality depends on daily ledger alignment with aggregate days (commission may be 0 on some days).
- Cost-structure insight can overlap Business Signals on the same share % (known residual from C1).
- Does not change backend KPIs or profit formulas.

## Tests

`frontend/src/views/dashboard/chart-insights.test.ts`

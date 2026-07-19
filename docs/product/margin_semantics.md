# Margin semantics (seller-facing)

**Production baseline:** FE surface Phase 9.16-C (bundle `DVVPbWvu`); platform SHA `f85dea6`  
**Rule:** labels and hints only — **no formula changes**.

Three different margins exist in the product. They must not share a bare «Маржа» label.

## Catalog

| UI label | Where | Backend source | Formula | Seller meaning |
|----------|-------|----------------|---------|----------------|
| **Маржа по выплате** | Dashboard hero, Financial Summary | `seller_kpis.margin_pct` via finance / revenue summary | `(total_to_pay − COGS) / revenue × 100` | Cash left after WB settlement fees, then COGS |
| **Маржа SKU** | Top SKU card / tab | `top_skus` → `sku_daily_metrics` | `Σ net_profit / Σ revenue × 100` | SKU-attributed ledger P&L − COGS |
| **Маржа (юнит-экономика)** | Economics table, SKU drilldown | `sku_unit_economics_daily` | `contribution_margin / revenue × 100` | Full fee stack contribution margin |

## Static hints (UI)

| Label | Hint text |
|-------|-----------|
| Маржа по выплате | `(Выплата − себестоимость) / выручка` |
| Маржа SKU | `Прибыль товара / его выручка` |
| Маржа (юнит-экономика) | `После всех расходов WB и себестоимости` |

Constants: `frontend/src/views/dashboard/margin-labels.ts`  
Hint chip: `frontend/src/views/dashboard/MetricInfoHint.tsx`

## Why numbers differ

- Settlement margin uses **payout path** (total_to_pay), not full ledger fee sum.
- Top SKU uses **SKU-attributed** ledger profit.
- Economics uses **unit-economics contribution** with the complete fee stack.

Trust gating (`profit_metrics_trust`) still hides or estimates profit/margin when COGS coverage is incomplete — labels do not override trust.

## Related

- [seller_kpis.py](../../app/domain/analytics/seller_kpis.py) — settlement KPIs  
- [sku_unit_economics.md](../economics/sku_unit_economics.md)  
- [financial_semantics.md](../analytics/financial_semantics.md)  
- [seller_dashboard.md](../frontend/seller_dashboard.md)

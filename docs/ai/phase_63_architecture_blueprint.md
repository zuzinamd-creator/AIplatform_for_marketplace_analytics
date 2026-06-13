# PHASE 6.3 — Business Coverage Expansion Architecture Blueprint

**Проект:** AI Operational Director для продавцов Wildberries и Ozon  
**Статус:** Архитектурный проект (без реализации)  
**Дата:** 2026-06-07  
**Baseline после Phase 6.2.2:** Business Coverage 50%, AI Readiness 85.7, Seller Usefulness 74.1, Actionable Rate 100%, Dashboard Echo 0%

---

## 1. Текущее состояние

### 1.1 Архитектура данных (as-is)

```text
Upload (WB realization xlsx/csv)
  → WbFinancialProcessor
  → financial_ledger_entries (append-only)
  → inventory_ledger_entries
  → warehouse_stock_snapshots (rebuild)
  → daily_aggregates / sku_daily_metrics
  → sku_unit_economics_daily (+ cost_history COGS)
  → AI Intelligence Engine
      → 10 domain analysts (deterministic)
      → Insight Composer → AIRecommendation
      → Business Coverage V1 (block model)
```

**Ключевое ограничение:** нет live API sync с WB/Ozon. Данные поступают только через ручную загрузку файлов. Ozon — enum + placeholder ETL без парсера.

### 1.2 Покрытые домены (Business Coverage V1 = 50%)

| Блок | Вес | Статус | Источник |
|------|-----|--------|----------|
| Продажи | 12 | ✅ ON | `daily_aggregates`, `sku_daily_metrics` |
| Расходы маркетплейса | 14 | ✅ ON | `sku_unit_economics_daily`, ledger |
| Себестоимость и маржа | 14 | ✅ ON | `cost_history` + unit economics |
| Остатки и закупки | 10 | ✅ ON (частично) | `warehouse_stock_snapshots` |
| Продвижение на MP | 12 | ❌ OFF | — |
| Внешний маркетинг | 10 | ❌ OFF | — |
| Налоговая нагрузка | 10 | ❌ OFF | — |
| Операционные расходы | 10 | ❌ OFF | — |
| Финансовые расходы | 8 | ❌ OFF | — |

**Формула V1:** `Coverage = Σ(weight блоков с данными) / 100 × 100%` → 12+14+14+10 = **50%**

### 1.3 AI Pipeline (production)

- **10 domain analysts:** Sales, RevenueChange, Logistics, Returns, Concentration, Ads (stub), Inventory (limited), Funnel, MarketplaceComparison, Anomaly
- **Deep period insights:** unprofitable SKUs, high logistics/commission, period-over-period causes
- **Governed signals:** `_coverage_signals()` из `sku_unit_economics_daily`, `daily_aggregates`, `warehouse_stock_snapshots`
- **Insight Composer:** приоритизация L1 (revenue/profit/logistics) → L3 (KPI echo), формат «Что / Почему / Уверенность / Действие»
- **Operating Director scaffold** (`app/ai/director/`): Coverage V2, Data Quality Auditor, 8 domain experts, 3 cross-domain analysts — **не в production**

### 1.4 Качество AI (Phase 6.2.2)

| Метрика | Значение | Цель |
|---------|----------|------|
| Actionable Rate | 100% | ✅ |
| Dashboard Echo | 0% | ✅ |
| Seller Usefulness | 74.1 | ✅ (≥65) |
| AI Readiness | 85.7 | ✅ (≥75) |
| Business Coverage | 50% | ❌ (цель Phase 6.3) |
| Insight Quality | 84.2 | ✅ |

**Вывод:** AI качественно анализирует имеющиеся данные, но не может отвечать на вопросы о рекламе, конверсии, налогах, OPEX и полноценной inventory intelligence.

---

## 2. Аудит данных

### 2.1 Сводная таблица по бизнес-блокам

| Блок | Источник данных | Таблицы | Используются сейчас | Готовность к внедрению |
|------|-----------------|---------|---------------------|------------------------|
| **Revenue / Sales** | WB realization report upload | `financial_ledger_entries`, `daily_aggregates`, `sku_daily_metrics` | ✅ Полностью — analytics, AI, dashboard | **Production** |
| **Profit / Margin** | Ledger + `cost_history` | `sku_unit_economics_daily`, `cost_history` | ✅ С trust gating при COGS < 100% | **Production** |
| **Marketplace Costs** | WB realization report | `financial_ledger_entries`, `sku_unit_economics_daily` | ✅ Commission, logistics, storage, penalties, deductions | **Production** |
| **Unit Economics** | Rebuild from ledger | `sku_unit_economics_daily` | ✅ Economics page, deep insights, governed signals | **Production** |
| **Inventory — остатки** | Derived from WB finance rows | `inventory_ledger_entries`, `warehouse_stock_snapshots` | ⚠️ Частично — analytics endpoints exist, AI limited | **Partial — needs enrichment** |
| **Inventory — движение** | WB finance operation types | `inventory_ledger_entries` | ⚠️ ETL only, не в AI insights | **Partial** |
| **Inventory — дни покрытия** | — | — | ❌ Нет расчёта | **Not ready — needs sales velocity + stock** |
| **Inventory — out of stock** | — | — | ❌ Нет детекции OOS | **Not ready — needs stock API or daily snapshots** |
| **Advertising — расходы** | WB realization `advertisement` column (if present) | `financial_ledger_entries` (ADVRTISEMENT), `sku_unit_economics_daily.ads` | ⚠️ Инфраструктура есть, pilot data = 0 | **Partial — column often empty** |
| **Advertising — показы/клики/CTR** | — | — | ❌ Нет таблиц, нет ETL | **Not ready** |
| **Advertising — CPC/ACOS/ДРР/ROMI** | — | — | ❌ Coverage flags hardcoded False | **Not ready — needs ads report + revenue link** |
| **Conversion — просмотры** | — | — | ❌ | **Not ready** |
| **Conversion — корзина** | — | — | ❌ | **Not ready** |
| **Conversion — конверсия карточки** | — | — | ❌ `card_conversion_available` never set | **Not ready** |
| **Taxes — УСН** | — | — | ❌ Coverage flag only | **Not ready — manual import planned** |
| **Taxes — НДС** | — | — | ❌ | **Not ready** |
| **Taxes — страховые взносы** | — | — | ❌ | **Not ready** |
| **OPEX — зарплаты** | — | — | ❌ `opex_payroll_available` never set | **Not ready — manual import planned** |
| **OPEX — аренда** | — | — | ❌ | **Not ready** |
| **OPEX — подрядчики** | — | — | ❌ | **Not ready** |
| **OPEX — прочие** | Partial via `cost_history.additional_cost` | `cost_history` | ⚠️ Только COGS-side, не seller OPEX | **Partial** |
| **Financial expenses** | — | — | ❌ | **Not ready** |
| **External marketing** | — | — | ❌ | **Not ready** |
| **Ozon data** | — | — | ❌ Placeholder ETL only | **Not ready** |

### 2.2 Детальный аудит: Inventory

| Подблок | Данные в системе | Таблицы есть, не используются | Данных нет |
|---------|------------------|-------------------------------|------------|
| Остатки (stock level) | ✅ `actual_stock`, `opening_stock` per SKU/warehouse/day | `warehouse_stock_snapshots_staging` (ETL only) | Real-time stock from WB API |
| Движение остатков | ✅ `inventory_ledger_entries` (sale, return, loss, writeoff, inbound) | Ledger not read by AI directly | Procurement/inbound planning data |
| Дни покрытия (days of cover) | ❌ | — | Sales velocity × stock formula not implemented |
| Out of stock | ❌ | `discrepancy_units` exists but no OOS flag | WB stock report, zero-stock detection |
| Медленно оборачиваемые | ⚠️ Analytics method `inventory_slow_movers()` exists | Not wired to AI InventoryAnalyst | Turnover benchmark thresholds |
| Мёртвый сток | ⚠️ Analytics method `inventory_dead_stock()` exists | Not wired to AI | Days-without-sale threshold config |
| Замороженный капитал | ⚠️ Computable from stock × COGS | `inventory_frozen_capital_available` flag never set | — |
| Прогноз дефицита | ❌ | — | Demand forecast, lead time, reorder point |
| Потерянные продажи | ❌ | — | OOS correlation with sales drop |

### 2.3 Детальный аудит: Advertising

| Метрика | Данные в системе | Таблицы есть, не используются | Данных нет |
|---------|------------------|-------------------------------|------------|
| Расходы на рекламу | ⚠️ Column `advertisement` in WB report → ledger | `sku_unit_economics_daily.ads`, `ad_cost_ratio` ready | Dedicated ads report parser |
| Показы (impressions) | ❌ | — | WB Ads API / ads statistics report |
| Клики | ❌ | — | Same |
| CTR | ❌ | `ad_ctr_available` in Coverage V2 | Impressions + clicks |
| CPC | ❌ | — | Spend / clicks |
| ACOS | ❌ | — | Ad spend / ad-attributed revenue |
| ДРР (ad cost ratio) | ⚠️ Column exists in unit economics | Not populated when ads = 0 | Ad spend data |
| ROMI | ❌ | — | (Revenue from ads − ad spend) / ad spend |

### 2.4 Детальный аудит: Conversion

| Метрика | Данные в системе | Таблицы есть, не используются | Данных нет |
|---------|------------------|-------------------------------|------------|
| Просмотры карточки | ❌ | — | WB Analytics / Ozon analytics report |
| Добавления в корзину | ❌ | — | Same |
| Конверсия карточки | ❌ | `card_conversion_available` in Coverage V2 | Views → orders funnel |
| CTR карточки | ❌ | `card_ctr_available` | Search impressions + clicks |
| Buyout rate (proxy) | ✅ `buyout_rate` in aggregates | Not used in conversion analyst | — |
| Return rate (proxy) | ✅ `return_rate` in aggregates | Used by ReturnsAnalyst | — |

### 2.5 Детальный аудит: Taxes & OPEX

| Подблок | Данные в системе | Таблицы есть, не используются | Данных нет |
|---------|------------------|-------------------------------|------------|
| УСН | ❌ | Coverage flag `tax_usn_available` | `seller_tax_entries` table (planned) |
| НДС | ❌ | Coverage flag `tax_vat_available` | Same |
| Страховые взносы | ❌ | Coverage flag `tax_insurance_available` | Same |
| Патент | ❌ | Coverage flag `tax_patent_available` | Same |
| Зарплаты (ФОТ) | ❌ | Coverage flag `opex_payroll_available` | `seller_opex_entries` table (planned) |
| Аренда | ❌ | Coverage flag `opex_rent_available` | Same |
| Подрядчики | ❌ | Coverage flag `opex_contractors_available` | Same |
| Seller COGS | ✅ | `cost_history` (product, packaging, inbound) | — |
| Marketplace fees | ✅ | Ledger + unit economics | — |

### 2.6 Таблицы: использование vs потенциал

| Таблица | Статус | Потенциал Phase 6.3 |
|---------|--------|---------------------|
| `warehouse_stock_snapshots` | Analytics ✅, AI ⚠️ | Inventory Intelligence core |
| `inventory_ledger_entries` | ETL only | Movement analysis, loss detection |
| `sku_unit_economics_daily.ads` | Column ready, data empty | Advertising Intelligence core |
| `financial_ledger_entries` (ADVERTISEMENT) | Op type ready | Ad spend aggregation |
| `cost_history` | Production | Frozen capital, true margin |
| `metrics` (legacy) | Unused | Deprecate — superseded by aggregates |
| *No ads metrics table* | Missing | **New table needed (Phase 6.3+)** |
| *No conversion table* | Missing | **New table needed** |
| *No tax/opex tables* | Missing | **New tables needed (manual import)** |

---

## 3. Business Coverage Map

### 3.1 Текущее vs целевое покрытие

```text
                    CURRENT (V1)              TARGET (V1 post-6.3)
Sales               ████████████ 12           ████████████ 12
MP Costs            ██████████████ 14         ██████████████ 14
COGS                ██████████████ 14         ██████████████ 14
Inventory           ██████████ 10 (partial)   ██████████ 10 (full)
Promotion (ads)     ░░░░░░░░░░░░ 0            ████████████ 12
External mktg       ░░░░░░░░░░░░ 0            ░░░░░░░░░░░░ 0 *
Tax                 ░░░░░░░░░░░░ 0            ██████████ 10
OPEX                ░░░░░░░░░░░░ 0            ██████████ 10
Financial exp       ░░░░░░░░░░░░ 0            ░░░░░░░░░░░░ 0 *

TOTAL V1:           50/100 = 50%              82/100 = 82%
```

*External marketing и financial expenses — Phase 7+ (не в scope 6.3 MVP expansion)

### 3.2 Вклад каждого блока Intelligence

| Intelligence Block | V1 Weight | Expected Sub-signals ON | Coverage Contribution | AI Readiness Impact |
|--------------------|-----------|-------------------------|----------------------|---------------------|
| **Inventory Intelligence** | 10 (full activation) | inventory_signals, turnover, frozen_capital, procurement | **+0–5%** (partial→full within block) | +3–5 pts (Risk analyst, OOS insights) |
| **Advertising Intelligence** | 12 | ad_spend, ACOS, DRR, ROMI | **+12%** (biggest single block) | +8–10 pts (Growth analyst, causal ad chains) |
| **Conversion Intelligence** | — (V2 dim: 8+8=16) | card_views, cart_adds, conversion, CTR | **+8–16%** (V2 model) | +5–7 pts (Product Card expert) |
| **Tax Intelligence** | 10 | USN, VAT, insurance | **+10%** | +4–6 pts (Profit cross-analyst) |
| **OPEX Intelligence** | 10 | payroll, rent, contractors | **+10%** | +4–6 pts (true net profit) |

### 3.3 Coverage V2 projection

| Scenario | V2 Score | Domains ON |
|----------|----------|------------|
| Pilot today (WB only) | ~28–35% | sales, MP economics, COGS partial |
| + Ads spend report | ~45–50% | + promotion |
| + Ads CTR/impressions | ~55–60% | + ctr |
| + Card conversion report | ~63–68% | + conversion |
| + Inventory full | ~73–78% | + inventory full |
| + Tax import | ~83–88% | + tax |
| + OPEX import | ~93–98% | + opex |

### 3.4 Приоритет расширения (impact × feasibility)

| Rank | Block | Coverage Δ | Feasibility | Rationale |
|------|-------|------------|-------------|-----------|
| 1 | **Advertising Intelligence** | +12% V1 | Medium — WB ads report upload | Highest seller demand; unlocks Growth cross-analyst |
| 2 | **Inventory Intelligence** | +0–5% V1, high insight value | High — data partially exists | Low-hanging fruit; tables ready |
| 3 | **Tax Intelligence** | +10% V1 | High — manual CSV import | Simple schema; high profit accuracy |
| 4 | **OPEX Intelligence** | +10% V1 | High — manual CSV import | True operational profit |
| 5 | **Conversion Intelligence** | +16% V2 | Medium — WB analytics report | Requires new report parser |

---

## 4. Inventory Intelligence Design

### 4.1 Данные: что есть

| Signal | Source | Table/Field | Status |
|--------|--------|-------------|--------|
| Stock level per SKU/warehouse/day | WB finance rows → rebuild | `warehouse_stock_snapshots.actual_stock` | ✅ Available |
| Opening stock, sold, returned, lost | Snapshot rebuild | `opening_stock`, `sold_units`, `returned_units`, `lost_units` | ✅ Available |
| Discrepancy (ledger vs snapshot) | Integrity check | `discrepancy_units`, `discrepancy_cost` | ✅ Available |
| Inventory movements | Ledger builder | `inventory_ledger_entries` | ✅ ETL, not AI |
| COGS for frozen capital | Cost history | `cost_history.product_cost` | ✅ Available |
| Sales velocity | Aggregates | `sku_daily_metrics.units_sold` | ✅ Available |
| Unit economics per SKU | Rebuild | `sku_unit_economics_daily` | ✅ Available |

### 4.2 Данные: чего не хватает

| Gap | Why needed | Proposed source |
|-----|------------|-----------------|
| Daily stock from WB Stock API | Real-time OOS detection | WB `/api/v3/stocks` or stock report upload |
| Lead time / reorder point | Deficit forecast | Seller manual config or procurement import |
| In-transit / procurement pipeline | Upcoming stock | Procurement import table |
| Historical OOS events | Lost sales correlation | Derived: stock=0 AND sales>0 prior day |
| Category-level stock benchmarks | Slow mover thresholds | Config or industry defaults |
| Multi-warehouse allocation | Transfer recommendations | WB warehouse report |

### 4.3 Архитектура Inventory Intelligence

```text
┌─────────────────────────────────────────────────────────┐
│ DATA LAYER                                              │
│  warehouse_stock_snapshots (existing)                   │
│  inventory_ledger_entries (existing)                    │
│  sku_daily_metrics.units_sold (existing)                │
│  cost_history (existing)                                │
│  + inventory_daily_metrics (NEW — derived, no API)      │
│  + stock_report_uploads (NEW — optional WB stock file)  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ COMPUTE LAYER (InventoryMetricsBuilder)                 │
│  days_of_cover = stock / avg_daily_sales(7d)            │
│  turnover_rate = COGS / avg_inventory_value             │
│  frozen_capital = Σ(stock × unit_cost)                  │
│  oos_flag = stock == 0 AND avg_sales_7d > 0           │
│  lost_sales_est = avg_daily_sales × oos_days            │
│  stockout_risk = days_of_cover < lead_time_threshold    │
│  slow_mover = turnover < category_p25                   │
│  dead_stock = no_sales_30d AND stock > 0                │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ AI LAYER                                                │
│  InventoryAnalyst (enhanced)                            │
│  RiskAnalyst (cross-domain: OOS → revenue)              │
│  Coverage signals: turnover, frozen_capital, procurement  │
└─────────────────────────────────────────────────────────┘
```

### 4.4 Инсайты (target)

| Insight ID | Trigger | Root Cause | Action |
|------------|---------|------------|--------|
| `inv_stockout_risk` | days_of_cover < 7 AND sales trending up | Low stock vs demand | Reorder SKU X, N units within Y days |
| `inv_lost_sales` | OOS detected, prior 7d avg sales > 0 | Zero stock on warehouse W | Expedite replenishment; estimate lost revenue |
| `inv_slow_mover` | turnover < threshold, stock > 30d cover | Overstock / weak demand | Markdown, bundle, or pause procurement |
| `inv_dead_stock` | no sales 30d+, stock > 0 | Obsolete / visibility issue | Liquidate or remove from assortment |
| `inv_excess_stock` | days_of_cover > 90 | Over-procurement | Reduce next order; consider promotion |
| `inv_frozen_capital` | frozen_capital > X% of revenue | Cash tied in inventory | Prioritize high-turnover SKUs |
| `inv_deficit_forecast` | stock / velocity < lead_time | Trend extrapolation | Schedule reorder before stockout |
| `inv_warehouse_imbalance` | stock skewed across warehouses | Uneven distribution | Transfer between warehouses |

### 4.5 Coverage signal activation

| Signal | Current | After Phase 6.3 |
|--------|---------|-----------------|
| `inventory_signals_available` | ✅ (snapshots exist) | ✅ |
| `inventory_turnover_available` | ❌ | ✅ (computed) |
| `inventory_frozen_capital_available` | ❌ | ✅ (computed) |
| `inventory_procurement_available` | ❌ | ⚠️ (manual import, Phase 6.3b) |
| `inventory_oos_available` | ❌ | ✅ (derived from snapshots) |

---

## 5. Advertising Intelligence Design

### 5.1 Данные WB/Ozon: что доступно на маркетплейсах

| Data Point | WB Source | Ozon Source | Currently Collected |
|------------|-----------|-------------|---------------------|
| Ad spend (total) | Realization report `advertisement` column; Ads cabinet export | Ozon Performance report | ⚠️ WB column only (often empty) |
| Ad spend per campaign | WB Ads → Statistics export (xlsx) | Ozon Performance API/report | ❌ |
| Ad spend per SKU | WB Ads SKU report | Ozon SKU-level ads | ❌ |
| Impressions | WB Ads statistics | Ozon ads analytics | ❌ |
| Clicks | WB Ads statistics | Ozon ads analytics | ❌ |
| CTR | Computed | Computed | ❌ |
| CPC | Computed (spend/clicks) | Computed | ❌ |
| Orders from ads | WB Ads attribution | Ozon attributed orders | ❌ |
| ACOS | spend / ad revenue | Same | ❌ |
| ДРР | spend / total revenue | Same | ⚠️ Column ready, empty |
| ROMI | (ad revenue − spend) / spend | Same | ❌ |

### 5.2 Данные: что уже собирается

- `financial_ledger_entries` with `operation_type = ADVERTISEMENT` (when WB report has `advertisement` column)
- `sku_unit_economics_daily.ads` — aggregated ad spend per SKU/day
- `sku_unit_economics_daily.ad_cost_ratio` — ДРР when ads > 0
- `governed_signals.ad_spend_available` — boolean from ads sum
- `AdsAnalyst` — returns `ads_no_governed_spend` when ads = 0

### 5.3 Данные: что необходимо догрузить

**Phase 6.3a — Ad Spend (minimum viable):**

| Source | Format | Fields | Priority |
|--------|--------|--------|----------|
| WB Ads Statistics report | xlsx upload | date, campaign, sku, spend | P0 |
| WB Realization (existing) | xlsx | advertisement column | P0 (already supported) |

**Phase 6.3b — Ad Performance (full):**

| Source | Format | Fields | Priority |
|--------|--------|--------|----------|
| WB Ads Statistics (extended) | xlsx | + impressions, clicks, orders, revenue | P1 |
| Ozon Performance report | xlsx | spend, impressions, clicks, orders | P1 (after Ozon ETL) |

### 5.4 Архитектура Advertising Intelligence

```text
┌─────────────────────────────────────────────────────────┐
│ DATA LAYER                                              │
│  financial_ledger_entries.ADVERTISEMENT (existing)      │
│  sku_unit_economics_daily.ads (existing)                │
│  + ad_campaign_daily_metrics (NEW)                      │
│  + ad_sku_daily_metrics (NEW)                           │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ COMPUTE LAYER (AdMetricsBuilder)                        │
│  DRR = ad_spend / total_revenue                         │
│  ACOS = ad_spend / ad_attributed_revenue                │
│  ROMI = (ad_revenue − ad_spend) / ad_spend              │
│  CPC = ad_spend / clicks                                │
│  CTR = clicks / impressions                             │
│  organic_growth = total_rev_delta − ad_attributed_delta │
│  ad_dependency = ad_rev / total_rev                     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ AI LAYER                                                │
│  AdsAnalyst (full)                                      │
│  GrowthAnalyst (cross-domain)                           │
│  Coverage: promotion block ON (+12% V1)                 │
└─────────────────────────────────────────────────────────┘
```

### 5.5 Инсайты (target)

| Insight ID | Trigger | Root Cause | Action |
|------------|---------|------------|--------|
| `ads_spend_growth_revenue` | ad spend ↑ AND revenue ↑ | Paid traffic driving sales | Monitor ROMI; scale if ROMI > threshold |
| `ads_organic_growth` | revenue ↑, ad spend flat | Organic demand / seasonality | Maintain current ad level; investigate drivers |
| `ads_inefficient_campaign` | ACOS > margin OR ROMI < 0 | Overbidding / wrong keywords | Pause or reduce budget on campaign X |
| `ads_revenue_up_profit_down` | revenue ↑, profit ↓, ads ↑ | Ad spend exceeds margin | Cut spend on low-ROMI SKUs |
| `ads_dependency_risk` | ad_rev / total_rev > 60% | Business dependent on paid traffic | Diversify: SEO, organic, external channels |
| `ads_sku_waste` | SKU ad spend > 0, SKU profit < 0 | Advertising unprofitable SKU | Stop ads on SKU X |
| `ads_ctr_decline` | CTR ↓ 20%+ WoW | Creative fatigue / relevance drop | Refresh creatives, review targeting |
| `ads_no_data` | ad_spend_available = false | Missing ads report | Upload WB Ads Statistics (existing message) |

---

## 6. Conversion Intelligence Design

### 6.1 Данные WB/Ozon

| Metric | WB Source | Ozon Source | Status |
|--------|-----------|-------------|--------|
| Card views | WB Seller Analytics → "Воронка продаж" | Ozon Analytics → Product views | ❌ Not collected |
| Add to cart | WB funnel report | Ozon funnel | ❌ |
| Orders (from card) | WB funnel / sales report | Ozon orders | ✅ (via sales, not funnel) |
| Card conversion | views → orders | Same | ❌ |
| Search CTR | WB search analytics | Ozon search | ❌ |
| Buyout rate | Realization report | Ozon report | ✅ Proxy in aggregates |

### 6.2 Архитектура

```text
┌─────────────────────────────────────────────────────────┐
│ DATA LAYER                                              │
│  + card_funnel_daily_metrics (NEW)                      │
│    sku, date, views, cart_adds, orders, conversion_pct  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ COMPUTE LAYER                                           │
│  card_conversion = orders / views                       │
│  cart_conversion = orders / cart_adds                   │
│  funnel_drop_cart = 1 − (cart_adds / views)             │
│  funnel_drop_purchase = 1 − (orders / cart_adds)        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ AI LAYER: ProductCardAnalyst (DomainExpert)             │
│  Coverage V2: conversion=8, ctr=8                       │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Инсайты (target)

| Insight ID | Trigger | Action |
|------------|---------|--------|
| `conv_card_low` | card_conversion < category median | Improve photos, description, reviews |
| `conv_cart_abandon` | cart_adds high, orders low | Check price, delivery time, competitors |
| `conv_views_drop` | views ↓ 20%+ WoW | Check ranking, ads, stock availability |
| `conv_top_sku_funnel` | Top SKU low conversion | A/B test card content |

---

## 7. Tax & OPEX Design

### 7.1 Архитектура (manual import model)

```text
┌─────────────────────────────────────────────────────────┐
│ DATA LAYER (NEW tables — import only, no API)           │
│  seller_tax_entries                                     │
│    tenant, period, tax_type (USN/VAT/INSURANCE/PATENT)  │
│    amount, rate, base_amount, notes                     │
│  seller_opex_entries                                    │
│    tenant, period, category (PAYROLL/RENT/CONTRACTOR/   │
│              CONTENT/PACKAGING/OTHER)                   │
│    amount, description, recurring                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ COMPUTE LAYER                                           │
│  tax_burden_pct = total_tax / revenue                   │
│  opex_ratio = total_opex / revenue                      │
│  true_net_profit = mp_profit − tax − opex               │
│  break_even_revenue = opex / margin_pct                 │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ AI LAYER: TaxExpert, OperatingCostExpert                │
│  ProfitAnalyst (cross-domain): true profitability       │
│  Coverage: tax block +10%, opex block +10%              │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Import UX

| Import Type | Format | Required Fields | Frequency |
|-------------|--------|-----------------|-----------|
| Tax (УСН) | CSV/xlsx | period, amount, rate | Monthly/quarterly |
| Tax (НДС) | CSV/xlsx | period, amount | Monthly |
| Tax (взносы) | CSV/xlsx | period, amount | Quarterly |
| OPEX (ФОТ) | CSV/xlsx | period, amount, category | Monthly |
| OPEX (аренда) | CSV/xlsx | period, amount | Monthly |
| OPEX (подрядчики) | CSV/xlsx | period, amount, description | Monthly |

### 7.3 Инсайты (target)

| Insight ID | Trigger | Action |
|------------|---------|--------|
| `tax_usn_rate_check` | USN amount vs revenue inconsistent with declared rate | Verify with accountant |
| `tax_vat_impact` | VAT > X% of revenue | Review pricing strategy |
| `opex_revenue_ratio_high` | OPEX / revenue > 30% | Audit cost structure |
| `true_profit_negative` | MP profit > 0 but true profit < 0 after tax+opex | Urgent cost review |
| `break_even_exceeded` | Revenue < break-even | Reduce OPEX or increase sales |

---

## 8. Cross-Domain Intelligence Design

### 8.1 Проблема

Сейчас 10 domain analysts работают изолированно. После расширения coverage появляется возможность **причинно-следственных цепочек** через домены.

### 8.2 Cross-Domain Analysts (из Operating Director scaffold)

| Analyst | Input Domains | Purpose |
|---------|---------------|---------|
| **GrowthAnalyst** | Sales + Ads + Conversion | Revenue growth decomposition: organic vs paid |
| **ProfitAnalyst** | Sales + MP Costs + COGS + Tax + OPEX + Ads | True profitability chain |
| **RiskAnalyst** | Inventory + Sales + Concentration | Stockout, dependency, concentration risks |

### 8.3 Междоменные выводы (target)

| Scenario | Domains Involved | Cross-Domain Insight |
|----------|------------------|---------------------|
| Revenue ↑, Profit ↓ | Sales + Ads + MP Costs | «Выручка выросла на X%, но прибыль упала на Y% — основная причина: рост рекламных расходов (+Z тыс.), ДРР вырос с A% до B%» |
| Revenue ↓, Stock = 0 | Sales + Inventory | «Продажи SKU X упали на N% — товар отсутствовал на складе W последние M дней. Оценка потерянных продаж: K руб.» |
| Revenue ↑, Profit flat | Sales + Logistics + COGS | «Рост выручки +X% нивелирован ростом логистики (+Y п.п.) и себестоимости — маржа не изменилась» |
| Ads ↑, Conversion ↓ | Ads + Conversion | «Расходы на рекламу выросли, но конверсия карточки упала — возможно, реклама привлекает нецелевой трафик» |
| Revenue ↑, True Profit ↓ | Sales + Tax + OPEX | «Выручка растёт, но после налогов и OPEX чистая прибыль снижается — проверьте налоговую нагрузку и операционные расходы» |
| Top SKU OOS | Inventory + Concentration + Sales | «60% выручки зависит от 3 SKU; один из них (X) out of stock — критический риск выручки» |
| Ad-dependent growth | Ads + Sales + Profit | «80% роста выручки обеспечено рекламой; при отключении ads прогнозная выручка −X%» |
| Slow mover + Ad spend | Inventory + Ads | «SKU X — медленно оборачиваемый (turnover < 2), но на него тратится Z руб. рекламы — ROMI отрицательный» |

### 8.4 Архитектура Cross-Domain

```text
L1 Domain Experts (8)
  SalesExpert → findings[]
  AdvertisingExpert → findings[]
  InventoryExpert → findings[]
  TaxExpert → findings[]
  ...
       │
       ▼
L2 Cross-Domain Analysts (3)
  GrowthAnalyst(findings) → cross_findings[]
    rules:
      IF sales.revenue_up AND ads.spend_up AND ads.romi < threshold
        → "revenue_growth_ad_driven_unprofitable"
      IF sales.revenue_up AND NOT ads.spend_up
        → "revenue_growth_organic"
      IF sales.revenue_down AND inventory.oos_detected
        → "revenue_drop_stockout"

  ProfitAnalyst(findings) → cross_findings[]
    rules:
      IF sales.revenue_up AND profit.down AND ads.spend_up
        → "profit_eroded_by_ads"
      IF mp_profit > 0 AND true_profit < 0
        → "hidden_unprofitability"

  RiskAnalyst(findings) → cross_findings[]
    rules:
      IF concentration.top3 > 70% AND inventory.oos_any_top_sku
        → "concentration_stockout_risk"
      IF ads.dependency > 60%
        → "ad_dependency_risk"
       │
       ▼
L3 Executive Director
  Synthesize cross_findings → Seller Report
  (conclusions, causes, risks, actions, limitations)
```

### 8.5 Root Cause Confidence Enhancement

Cross-domain chains повышают `root_cause_confidence`:

| Chain Type | Confidence Boost | Example |
|------------|------------------|---------|
| Single-domain | 0.6–0.7 | «Логистика высокая» |
| Two-domain correlated | 0.75–0.85 | «Выручка ↓ + OOS» |
| Three-domain causal | 0.85–0.95 | «Выручка ↑ + Ads ↑ + Profit ↓» |

---

## 9. План внедрения

### 9.1 Этапы

```text
Phase 6.3.0 — Foundation (1 sprint)
  ├── InventoryMetricsBuilder (derived metrics from existing tables)
  ├── Enhanced InventoryAnalyst + RiskAnalyst OOS rules
  ├── Coverage signals: turnover, frozen_capital, oos
  └── No new tables; compute layer only

Phase 6.3.1 — Advertising ETL (1 sprint)
  ├── WB Ads Statistics report parser
  ├── ad_campaign_daily_metrics + ad_sku_daily_metrics tables
  ├── AdMetricsBuilder (DRR, ACOS, ROMI, CPC, CTR)
  ├── Full AdsAnalyst + GrowthAnalyst ad rules
  └── Coverage promotion block ON (+12% V1)

Phase 6.3.2 — Tax & OPEX Import (1 sprint)
  ├── seller_tax_entries + seller_opex_entries tables
  ├── CSV/xlsx import endpoints
  ├── TaxExpert + OperatingCostExpert
  ├── ProfitAnalyst true profit chain
  └── Coverage tax + opex blocks ON (+20% V1)

Phase 6.3.3 — Conversion Funnel (1 sprint)
  ├── WB funnel report parser
  ├── card_funnel_daily_metrics table
  ├── ProductCardAnalyst
  └── Coverage V2 conversion + ctr dimensions

Phase 6.3.4 — Cross-Domain & Operating Director (1 sprint)
  ├── Enable OperatingDirectorPipeline (feature flag)
  ├── Cross-domain analysts production
  ├── Executive Director report in UI
  └── Shadow-run audit vs legacy pipeline

Phase 6.3.5 — Ozon Foundation (1 sprint, parallel track)
  ├── Ozon finance report parser
  ├── Ozon ads report parser
  └── MarketplaceComparisonAnalyst activation
```

### 9.2 Приоритеты

| Priority | Stage | Coverage Impact | Seller Value | Complexity |
|----------|-------|-----------------|--------------|------------|
| **P0** | 6.3.0 Inventory | +0–5% V1, high insights | High — stockout/lost sales | **Low** (existing data) |
| **P0** | 6.3.1 Advertising | +12% V1 | **Highest** — #1 upload priority | **Medium** (new parser) |
| **P1** | 6.3.2 Tax & OPEX | +20% V1 | High — true profit | **Low** (CSV import) |
| **P1** | 6.3.4 Cross-Domain | Qualitative boost | High — causal chains | **Medium** (wiring) |
| **P2** | 6.3.3 Conversion | +16% V2 | Medium — card optimization | **Medium** (new parser) |
| **P3** | 6.3.5 Ozon | Multi-MP | Medium — Ozon sellers | **High** (full ETL) |

### 9.3 Оценка сложности

| Component | Effort | Risk | Dependencies |
|-----------|--------|------|--------------|
| InventoryMetricsBuilder | 3–5 days | Low | warehouse_stock_snapshots, sku_daily_metrics |
| WB Ads parser | 5–8 days | Medium | Sample ads reports, column mapping |
| Tax/OPEX import | 3–5 days | Low | Schema design, CSV validation |
| Conversion funnel parser | 5–8 days | Medium | WB funnel report format |
| Cross-domain wiring | 5–8 days | Medium | All L1 experts producing findings |
| Operating Director activation | 3–5 days | Low | Scaffold exists, feature flag |
| Ozon ETL | 10–15 days | High | Ozon report samples, semantics |

### 9.4 Риски

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| WB ads report format changes | Medium | High | Semantics versioning (existing pattern) |
| Ads column empty in realization reports | High | Medium | Dedicated ads report upload (6.3.1) |
| Sellers won't upload tax/opex | Medium | Medium | Smart defaults, quarterly reminders, partial coverage |
| Coverage V2 score drop vs V1 | Certain | Medium | Show both scores; explain granularity |
| Cross-domain false causation | Medium | High | Confidence thresholds; require 2+ correlated signals |
| Inventory OOS false positives | Low | Medium | Require 2+ consecutive zero-stock days |
| Ozon report format unknown | High | High | Defer to 6.3.5; focus WB first |

### 9.5 Зависимости

```text
6.3.0 Inventory ──────────────────────────┐
                                           │
6.3.1 Advertising ──────────────────┐      │
                                     ▼      ▼
                              6.3.4 Cross-Domain ──→ Operating Director
                                     ▲
6.3.2 Tax/OPEX ─────────────────────┘
                                     
6.3.3 Conversion ──→ (feeds Cross-Domain, optional parallel)

6.3.5 Ozon ──→ (independent track, feeds MarketplaceComparison)
```

### 9.6 Что НЕ входит в Phase 6.3

- Live WB/Ozon API sync (Phase 7, roadmap item #17)
- External marketing (Yandex, VK, Telegram)
- Financial expenses (loans, leasing)
- ML-based demand forecasting
- LLM at L3 Executive Director (optional Phase 6.3.4+)
- Frontend redesign (Director report sections reuse existing UI)

---

## 10. Оценка ожидаемого роста Business Coverage и AI Readiness

### 10.1 Business Coverage projection

| Milestone | V1 Coverage | V2 Coverage | Blocks ON |
|-----------|-------------|-------------|-----------|
| **Baseline (6.2.2)** | 50% | ~30% | sales, MP costs, COGS, inventory partial |
| **After 6.3.0** (inventory full) | 50–55% | ~38% | + turnover, frozen capital, OOS |
| **After 6.3.1** (ads) | 62–67% | ~50% | + promotion |
| **After 6.3.2** (tax+opex) | 82–87% | ~70% | + tax, opex |
| **After 6.3.3** (conversion) | 82–87% | ~85% | + conversion, ctr |
| **After 6.3.4** (cross-domain) | 82–87% | ~85% | qualitative ↑ |
| **Target (full 6.3)** | **~82%** | **~85%** | 7/9 V1 blocks |

### 10.2 AI Readiness projection

| Factor | Current | After 6.3 | Delta |
|--------|---------|-----------|-------|
| Actionable Rate | 100% | 100% (maintain) | 0 |
| Dashboard Echo | 0% | 0% (maintain) | 0 |
| Seller Usefulness | 74.1 | 82–88 (est.) | +8–14 |
| Root Cause Confidence | 0.7 avg | 0.85 avg (cross-domain) | +0.15 |
| Blocked Analysts | 3–4 of 10 | 0–1 of 10 | −3 |
| Insight Depth (causal chains) | Single-domain | Multi-domain | Qualitative ↑ |
| **AI Readiness** | **85.7** | **92–95 (est.)** | **+7–10** |

### 10.3 Формула AI Readiness (extended)

```
AI Readiness = (
    actionable_rate × 0.25 +
    (100 − dashboard_echo) × 0.15 +
    seller_usefulness × 0.25 +
    business_coverage × 0.20 +
    root_cause_confidence × 100 × 0.15
)
```

| Scenario | Calculation | Result |
|----------|-------------|--------|
| Baseline | 100×0.25 + 100×0.15 + 74.1×0.25 + 50×0.20 + 70×0.15 | **85.3** ≈ 85.7 |
| After 6.3 full | 100×0.25 + 100×0.15 + 85×0.25 + 82×0.20 + 85×0.15 | **93.2** |

### 10.4 Success criteria Phase 6.3

| Metric | Target | Measurement |
|--------|--------|-------------|
| Business Coverage V1 | ≥ 80% | `assess_business_coverage()` on pilot user |
| Business Coverage V2 | ≥ 80% | `compute_coverage_v2()` on pilot user |
| AI Readiness | ≥ 92 | Phase 6.3 audit script |
| Seller Usefulness | ≥ 80 | Post-expansion audit |
| Cross-domain insights | ≥ 2 per report | Audit cross_findings count |
| Blocked analysts | ≤ 1 | Data Quality Auditor |
| Actionable Rate | 100% (maintain) | No regression |
| Dashboard Echo | 0% (maintain) | No regression |

---

## Appendix A: New Tables Summary (for implementation phase)

| Table | Phase | Purpose |
|-------|-------|---------|
| `inventory_daily_metrics` | 6.3.0 | Derived: days_of_cover, turnover, oos_flag, frozen_capital |
| `ad_campaign_daily_metrics` | 6.3.1 | Campaign-level ad performance |
| `ad_sku_daily_metrics` | 6.3.1 | SKU-level ad performance |
| `seller_tax_entries` | 6.3.2 | Manual tax import |
| `seller_opex_entries` | 6.3.2 | Manual OPEX import |
| `card_funnel_daily_metrics` | 6.3.3 | Card views, cart, conversion |

## Appendix B: File Map (existing → enhanced)

| Current File | Enhancement |
|--------------|-------------|
| `app/ai/analysts/inventory.py` | Full insights (6.3.0) |
| `app/ai/analysts/ads.py` | Full insights (6.3.1) |
| `app/ai/analysts/governed_signals.py` | New coverage signals |
| `app/ai/coverage/business_coverage.py` | No changes (V1 stable) |
| `app/ai/director/coverage_v2.py` | Activate dimensions |
| `app/ai/director/cross_domain.py` | Production rules |
| `app/ai/director/pipeline.py` | Feature flag activation |
| `app/etl/wb/processor.py` | Route ads/funnel reports |
| `app/services/analytics_service.py` | Inventory/ad API endpoints |

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| Business Coverage V1 | Block model: binary on/off per business block, weights sum to 100 |
| Business Coverage V2 | Dimension model: partial completeness per sub-signal |
| Governed Signals | Deterministic KPIs from DB → analysts (no LLM) |
| Deep Period Insights | SKU-level deterministic bullets from unit economics |
| Cross-Domain | Multi-analyst causal chains (L2 in Operating Director) |
| ДРР | Доля рекламных расходов = ad spend / revenue |
| ACOS | Advertising Cost of Sales = ad spend / ad revenue |
| ROMI | Return on Marketing Investment = (ad revenue − spend) / spend |
| OOS | Out of Stock |
| Frozen Capital | Stock value at cost = Σ(stock × unit_cost) |

---

*Документ подготовлен на основе аудита кодовой базы, Phase 6.2.2 metrics, и `docs/ai/operating_director_architecture.md`. Реализация не начата — только архитектурный проект.*

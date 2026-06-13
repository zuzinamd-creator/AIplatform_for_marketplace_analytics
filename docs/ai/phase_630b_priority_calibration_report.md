# Phase 6.3.0B — Priority Calibration Report

**Дата:** 2026-06-07  
**Pilot user:** `caefecb3-5789-4878-a9d4-929be573fbcc`  
**Scope:** `priority_engine.py` only — Intelligence Layer, Coverage Engine, Inventory вычисления **не изменялись**

---

## 1. Что было причиной деградации

Phase 6.3.0A установила цепочку:

```text
inventory_* → автоматический L1
  → collect_structured_insights: все L1 inventory в lead
  → pick_executive_lead: inventory первым
  → title + insight_quality = inventory (IQ 77.5)
  → seller_usefulness = 77.5 × 0.88 = 68.2
```

Revenue insight (`sales_top_sku`, IQ **84.2**) остался в Executive Lead #3 на **L2** и **не влиял** на usefulness.

**Inventory Intelligence работал корректно** — проблема была исключительно в **ranking / primary selection**.

---

## 2. Какие изменения внесены

| # | Изменение | Файл |
|---|-----------|------|
| 1 | **Revenue Protection Layer** — primary выбирается из revenue/profit pool, если IQ не ниже escalated inventory более чем на 8 п.п. | `priority_engine.py` |
| 2 | **Inventory Escalation Rules** — L1 только для `inventory_dead_stock` (high) и `inventory_frozen_capital` (high, ≥20% revenue) | `priority_engine.py` |
| 3 | **Inventory L2 default** — frozen_capital (medium), concentration, risk, slow_movers → supporting domain | `priority_engine.py` |
| 4 | **`sales_top_sku` → L1** — revenue protection для pilot-периодов | `priority_engine.py` |
| 5 | **Executive Summary Rebalancing** — domain-balanced lead: Revenue → Inventory (max 1 slot) → Other | `priority_engine.py` |
| 6 | **Inventory Deduplication** — semantic buckets (frozen/concentration/risk/dead/slow), deep bullets skip if analyst finding exists | `priority_engine.py` |
| 7 | **Deep inventory bullets → L2** — не конкурируют с revenue за primary | `priority_engine.py` |
| 8 | Unit tests для escalation и revenue protection | `test_inventory_intelligence.py`, `test_insight_engine.py` |

**Не изменялось:** `inventory.py`, `intelligence.py`, `business_coverage.py`, `composer.py` (логика lead[0] сохранена — меняется состав lead).

---

## 3. Новая логика приоритизации

### Priority Levels (Phase 6.3.0B)

| Finding | Severity | Level |
|---------|----------|-------|
| `sales_top_sku` | any | **L1** |
| `revenue_*`, `profit_*`, `logistics_*`, `returns_*`, `sales_low_margin` | any | **L1** |
| `inventory_dead_stock` | high/critical | **L1** (escalated) |
| `inventory_frozen_capital` | high (≥20% rev) | **L1** (escalated) |
| `inventory_frozen_capital` | medium | **L2** |
| `inventory_stock_concentration` | any | **L2** |
| `inventory_risk_high` | any | **L2** |
| `inventory_slow_movers` | any | **L2** |
| Deep inventory bullets | non-dead | **L2** |

### Primary Selection (Revenue Protection)

```text
1. Собрать revenue_pool (revenue, profit, margin, logistics, returns, concentration, sales_top_sku)
2. Собрать inv_escalated (inventory L1 only)
3. Если revenue_pool не пуст:
     primary = max(revenue_pool, by estimated IQ)
     Если inv_escalated IQ > revenue IQ + 8 → primary = inventory
4. Иначе если inv_escalated → primary = best inventory
5. Иначе → first candidate
```

---

## 4. Новая логика Executive Summary

### Lead composition (max 3 blocks)

```text
Slot 1: Primary (revenue-protected)
Slot 2: Next domain by order — inventory IF not primary AND max 1 inventory slot
Slot 3: Other domain or supporting insight
```

**Domain order:** Revenue → Profit → Margin → Logistics → Returns → Concentration → Inventory → Other

### Deduplication

- Semantic buckets: `inv:frozen`, `inv:concentration`, `inv:risk`, `inv:dead`, `inv:slow`
- One insight per bucket (highest estimated IQ wins)
- Deep bullets skipped when analyst finding with same `finding_id` already exists

---

## 5. Метрики до и после

| Метрика | 6.2.2 | 6.3.0 (pre-calibration) | **6.3.0B** | Цель | Статус |
|---------|-------|-------------------------|------------|------|--------|
| Seller Usefulness | 74.1 | 68.2 | **80.3** | ≥ 74 | ✅ |
| AI Readiness | 85.7 | 85.3 | **86.1** | ≥ 86 | ✅ |
| Primary Insight Quality | 84.2 | 77.5 | **91.2** | — | ✅ |
| Inventory Insight Rate | 0% | 100% | **100%** | сохранить | ✅ |
| Inventory Sub-Coverage | 25% | 75% | **75%** | — | ✅ |
| Dashboard Echo | 0% | 0% | **0%** | 0% | ✅ |
| Actionable Rate | 100% | 100% | **100%** | 100% | ✅ |
| Business Coverage V1 | 50% | 50% | **50%** | — | — |

**Phase 6.3.0B Audit decision: GO** (all calibration targets met)

---

## 6. Примеры Executive Summary

### Период 2026-05-25 — 2026-05-31

| | 6.2.2 | 6.3.0 | **6.3.0B** |
|---|-------|-------|------------|
| **Title** | Leading SKU j-31-239… | Заморожено 43 665 ₽… | **Leading SKU j-31-239…** |
| **Primary IQ** | 84.2 | 77.5 | **91.2** |
| **Usefulness** | 74.1 | 68.2 | **80.3** |
| Lead #1 | Revenue (L2) | Inventory (L1) | **Revenue (L1)** |
| Lead #2 | — | Inventory (L1) | **Inventory (L2)** frozen capital |
| Lead #3 | — | Inventory (L1) | **Inventory (L2)** concentration |

### Период 2026-05-18 — 2026-05-24

| | 6.3.0 | **6.3.0B** |
|---|-------|------------|
| Title | Заморожено 31 790 ₽… | **Leading SKU j-31-239…** |
| Lead #1 | Inventory | **Revenue** |
| Lead #2 | Inventory | **Inventory (supporting)** |
| Lead #3 | Revenue (L2) | mp_context (L3) |

### Распределение Primary Domain

| Domain | 6.2.2 | 6.3.0 | **6.3.0B** |
|--------|-------|-------|------------|
| Revenue | **100%** | 0% | **100%** |
| Inventory | 0% | **100%** | 0% |
| Profit | 0% | 0% | 0% |

### Распределение Executive Lead slots (all blocks)

| Domain | 6.2.2 | 6.3.0 | **6.3.0B** |
|--------|-------|-------|------------|
| Revenue | 100% | 19% | **25%** |
| Inventory | 0% | 81% | **50%** |
| Other | 0% | 0% | **25%** |

Inventory **сохранён в lead** как supporting domain (slot #2), но **не доминирует** title и usefulness.

---

## 7. Рекомендация: GO / NO-GO

### **GO** — обновление README и подготовка релиза v0.6-mvp-intelligence

**Обоснование:**

| Критерий | Статус |
|----------|--------|
| Inventory Intelligence сохранён | ✅ 100% insight rate, 75% sub-coverage |
| Seller Usefulness восстановлен | ✅ 80.3 > 74.1 baseline |
| AI Readiness ≥ 86 | ✅ 86.1 |
| Dashboard Echo = 0% | ✅ |
| Actionable Rate = 100% | ✅ |
| Revenue в центре Executive Summary | ✅ Primary 100% Revenue |
| Coverage Engine не изменён | ✅ 50% |
| Intelligence Layer не изменён | ✅ |

**Рекомендуемые next steps для v0.6:**

1. Обновить README: Phase 6.3.0 + 6.3.0B changelog
2. Tag `v0.6-mvp-intelligence`
3. Phase 6.3.1 — Advertising Intelligence (с revenue protection pattern)
4. Мониторинг: primary domain distribution в production audit

---

## Appendix — Audit command

```bash
.venv/bin/python3 scripts/phase_630_inventory_audit.py --limit 4
# Report: reports/phase_630_inventory_audit.json (phase 6.3.0B)
```

## Appendix — Key code references

- Escalation: `_inventory_escalates_to_l1()` in `app/ai/insights/priority_engine.py`
- Revenue protection: `_select_primary_insight()` 
- Lead balancing: `_balanced_executive_lead()`
- Dedup: `_dedupe_inventory_semantics()`, `_deep_bullet_redundant()`

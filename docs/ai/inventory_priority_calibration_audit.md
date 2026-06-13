# Inventory Priority Calibration Audit (Phase 6.3.0A)

**Дата:** 2026-06-07  
**Pilot user:** `caefecb3-5789-4878-a9d4-929be573fbcc`  
**Источники:** `reports/phase_622_insight_audit.json` (baseline 6.2.2), `reports/phase_630_inventory_audit.json`, текущие `AIRecommendation` в БД  
**Статус:** Только аудит — код не изменялся

---

## Executive Summary

После Phase 6.3.0 **Inventory Insight Rate вырос до 100%**, но **Seller Usefulness упал с 74.1 до 68.2 (−5.9 п.п.)**.

Корневая причина — **не качество inventory-данных**, а **калибровка приоритетов Executive Summary**:

1. Inventory-инсайты получили **Priority L1** и заняли **Primary Insight (title + usefulness driver)**.
2. Revenue-инсайт (`sales_top_sku`) **не удалён**, но **понижен до L2** и больше не определяет `seller_usefulness_score`.
3. `Seller Usefulness` вычисляется как `max(coverage_base, primary_insight_quality × 0.88)` — при IQ primary **77.5** вместо **84.2** получаем **68.2** вместо **74.1**.

---

## 1. Сводка метрик

| Метрика | До 6.3.0 (6.2.2) | После 6.3.0 | Δ |
|---------|------------------|-------------|---|
| Seller Usefulness | **74.1** | **68.2** | **−5.9** |
| AI Readiness | 85.7 | 85.3 | −0.4 |
| Avg Primary Insight Quality | **84.2** | **77.5** | **−6.7** |
| Inventory Insight Rate | 0% | 100% | +100% |
| Inventory Sub-Coverage | 25% (1/4) | 75% (3/4) | +50% |
| Dashboard Echo | 0% | 0% | 0 |
| Actionable Rate | 100% | 100% | 0 |

**Формула Seller Usefulness (production):**

```text
coverage_base = business_coverage × 0.55 + causal_bonus + action_bonus  ≈ 62.5
seller_usefulness_score = max(coverage_base, primary_insight_quality.overall × 0.88)
```

| Фаза | Primary IQ | × 0.88 | = Usefulness |
|------|------------|--------|--------------|
| 6.2.2 | 84.2 | 74.1 | **74.1** ✅ |
| 6.3.0 | 77.5 | 68.2 | **68.2** |

Падение usefulness **полностью объясняется** сменой primary insight и снижением его Insight Quality на 6.7 пунктов.

---

## 2. Задача 1 — Executive Summary: 20 сравниваемых слотов

> Pilot: 4 отчёта × 4 периода. До 6.3.0 сохранены 2 периода в audit JSON; после — все 4 периода из БД.  
> Ниже — **20 слотов** (Primary + Executive Lead blocks).

### ДО Phase 6.3.0 (6.2.2)

| # | Период | Роль | Primary Insight | Priority | IQ | Usefulness Δ |
|---|--------|------|-----------------|----------|-----|--------------|
| 1 | 2026-05-18 — 05-24 | **Primary (Title)** | Leading SKU j-31-239 in governed top-SKU list. | L2 | 84.2 | **74.1** |
| 2 | 2026-05-18 — 05-24 | Executive Lead #1 | Leading SKU j-31-239 in governed top-SKU list. | L2 | 84.2 | 74.1 |
| 3 | 2026-05-25 — 05-31 | **Primary (Title)** | Leading SKU j-31-239 in governed top-SKU list. | L2 | 84.2 | **74.1** |
| 4 | 2026-05-25 — 05-31 | Executive Lead #1 | Leading SKU j-31-239 in governed top-SKU list. | L2 | 84.2 | 74.1 |

**Insight Quality breakdown (6.2.2 primary):**

| Компонент | Score |
|-----------|-------|
| causal_depth | **25.0** |
| business_relevance | 18.0 (L2 bonus +10) |
| actionability | 15.0 |
| confidence | 21.2 |
| **overall** | **84.2** |

---

### ПОСЛЕ Phase 6.3.0

| # | Период | Роль | Primary Insight | Priority | IQ | Usefulness Δ |
|---|--------|------|-----------------|----------|-----|--------------|
| 5 | 2026-05-25 — 05-31 | **Primary (Title)** | Заморожено 43 665 ₽ в остатках (8.4% выручки) | **L1** | 77.5 | **68.2** |
| 6 | 2026-05-25 — 05-31 | Executive Lead #1 | Заморожено 43 666 ₽ в остатках на складе (8.4% выручки) | L1 | 73.8 | 64.9* |
| 7 | 2026-05-25 — 05-31 | Executive Lead #2 | Концентрация остатков: топ-3 SKU = 100% капитала | L1 | 86.5 | — |
| 8 | 2026-05-25 — 05-31 | Executive Lead #3 | Складской риск (high): концентрация капитала 100% | L1 | 86.2 | — |
| 9 | 2026-05-18 — 05-24 | **Primary (Title)** | Заморожено 31 790 ₽ в остатках (6.3% выручки) | **L1** | 77.5 | **68.2** |
| 10 | 2026-05-18 — 05-24 | Executive Lead #1 | Заморожено 31 791 ₽ в остатках на складе (6.3% выручки) | L1 | 73.8 | 64.9* |
| 11 | 2026-05-18 — 05-24 | Executive Lead #2 | Заморожено 31 790 ₽ в остатках (deep bullet duplicate) | L1 | 77.5 | — |
| 12 | 2026-05-18 — 05-24 | Executive Lead #3 | **Leading SKU j-31-239** in governed top-SKU list | **L2** | **84.2** | — |
| 13 | 2026-05-11 — 05-17 | **Primary (Title)** | Заморожено 15 557 ₽ в остатках (3.3% выручки) | **L1** | 77.5 | **68.2** |
| 14 | 2026-05-11 — 05-17 | Executive Lead #1 | Заморожено 15 557 ₽ в остатках на складе (3.3% выручки) | L1 | 73.8 | 64.9* |
| 15 | 2026-05-11 — 05-17 | Executive Lead #2 | Заморожено 15 557 ₽ (deep bullet duplicate) | L1 | 77.5 | — |
| 16 | 2026-05-11 — 05-17 | Executive Lead #3 | **Leading SKU j-31-239** in governed top-SKU list | **L2** | **84.2** | — |
| 17 | 2026-05-04 — 05-10 | **Primary (Title)** | Заморожено 15 557 ₽ в остатках (3.3% выручки) | **L1** | 77.5 | **68.2** |
| 18 | 2026-05-04 — 05-10 | Executive Lead #1 | Заморожено 15 557 ₽ в остатках на складе (3.3% выручки) | L1 | 73.8 | 64.9* |
| 19 | 2026-05-04 — 05-10 | Executive Lead #2 | Заморожено 15 557 ₽ (deep bullet duplicate) | L1 | 77.5 | — |
| 20 | 2026-05-04 — 05-10 | Executive Lead #3 | **Leading SKU j-31-239** in governed top-SKU list | **L2** | **84.2** | — |

\* Usefulness contribution применяется только к **Primary (Title)** — слоты #2–#20 не влияют на `seller_usefulness_score`.

**Insight Quality breakdown (6.3.0 primary):**

| Компонент | Score | Δ vs 6.2.2 |
|-----------|-------|------------|
| causal_depth | **12.0** | **−13.0** |
| business_relevance | **25.0** | +7.0 (L1 bonus +17) |
| actionability | 15.0 | 0 |
| confidence | 21.8 | +0.6 |
| **overall** | **77.5** | **−6.7** |

---

## 3. Задача 2 — Вытеснение Revenue / Profit / Margin

### Primary Insight (Title) — 100% displacement

| Домен | До 6.3.0 | После 6.3.0 |
|-------|----------|-------------|
| Revenue | **100%** (4/4) | **0%** (0/4) |
| Profit | 0% | 0% |
| Margin | 0% | 0% |
| Inventory | 0% | **100%** (4/4) |

**Вывод:** Inventory **полностью вытеснил Revenue из Primary Insight**. Profit/Margin **никогда не были primary** на pilot-периодах (нет L1 profit findings).

### Executive Lead body — частичное вытеснение

| Домен | До 6.3.0 (lead slots) | После 6.3.0 (lead slots) |
|-------|----------------------|--------------------------|
| Revenue | 100% (4/4) | **19%** (3/16) — только slot #3 |
| Inventory | 0% | **81%** (13/16) |
| Profit | 0% | 0% |
| Logistics | 0% | 0% |
| Returns | 0% | 0% |

**Revenue insight (`sales_top_sku`) сохранён** в Executive Lead #3 на 3 из 4 периодов, но:
- Priority понижен **L1 → L2**
- **Не влияет** на title, summary lead, `insight_quality`, `seller_usefulness_score`
- IQ Revenue insight **остался 84.2** — качество не деградировало, изменилась только **позиция**

### Дублирование Inventory в lead

После 6.3.0 в Executive Lead попадают **3–5 inventory-слотов** из разных источников:
- `InventoryAnalyst` findings (frozen_capital, stock_concentration, risk)
- `inventory_deep_bullets` (deep period insights)
- Дублирующие deep bullets с тем же текстом

Это **не снижает usefulness напрямую**, но **заполняет lead inventory-контентом** и вытесняет revenue из видимых top-3 blocks на 2 периодах из 4.

---

## 4. Задача 3 — Распределение Executive Lead по доменам

### Primary (Title) — определяет usefulness

| Домен | До 6.3.0 | После 6.3.0 |
|-------|----------|-------------|
| Revenue | **100%** | 0% |
| Profit | 0% | 0% |
| Logistics | 0% | 0% |
| Returns | 0% | 0% |
| Inventory | 0% | **100%** |
| Other | 0% | 0% |

### Все Executive Lead slots (Primary + Lead #1–#3)

| Домен | До 6.3.0 | После 6.3.0 |
|-------|----------|-------------|
| Revenue | **100%** | **19%** |
| Profit | 0% | 0% |
| Logistics | 0% | 0% |
| Returns | 0% | 0% |
| Inventory | 0% | **81%** |
| Other | 0% | 0% |

---

## 5. Задача 4 — Корневая причина падения Seller Usefulness

### Цепочка причинно-следственных факторов

```text
Phase 6.3.0: inventory_* → L1 в priority_engine
        ↓
collect_structured_insights: L1 inventory merged в lead даже при executive_insights
        ↓
pick_executive_lead: inventory L1 > revenue L2 (sales_top_sku)
        ↓
compose_insight_driven_output: title = lead[0] = inventory
        ↓
compute_insight_quality_score: только на primary (inventory, IQ 77.5)
        ↓
build_actionable_payload: seller_usefulness = IQ × 0.88 = 68.2
        ↓
Avg Seller Usefulness: 74.1 → 68.2 (−5.9)
```

### Декомposition Insight Quality (84.2 → 77.5)

| Фактор | Вклад в падение | Объяснение |
|--------|-----------------|------------|
| **causal_depth −13** | **Главный** | Inventory `why`: «Деньги заморожены в остатках…» — слабее проходит `_has_causal_analysis()` vs SKU-driven revenue text |
| business_relevance +7 | Компенсация | L1 inventory (+17) vs L2 revenue (+10) — недостаточно для offset |
| actionability 0 | — | Одинаково 15.0 |
| confidence +0.6 | — | Незначительно |

### Что НЕ является причиной

| Гипотеза | Статус |
|----------|--------|
| Dashboard Echo вырос | ❌ Остался 0% |
| Actionable Rate упал | ❌ Остался 100% |
| Inventory data quality плохая | ❌ Sub-coverage 75%, signals корректны |
| Revenue insights удалены | ❌ Сохранены на L2, IQ 84.2 |
| Coverage Engine V1 изменился | ❌ Остался 50% |
| Coverage base score упал | ❌ ~62.5 стабилен; доминирует IQ×0.88 |

---

## 6. Ответы на ключевые вопросы

### 1. Причина падения usefulness

**Смена Primary Insight с Revenue (IQ 84.2) на Inventory (IQ 77.5)** из-за присвоения inventory findings Priority L1 и выбора их как `lead[0]`. Seller Usefulness **жёстко привязан** к quality primary insight (`× 0.88`), а не к среднему по всем lead blocks.

### 2. Требуется ли корректировка приоритетов?

**Да.**

| Finding | Текущий Priority | Рекомендуемый |
|---------|------------------|---------------|
| `inventory_frozen_capital` | L1 | **L2** (informational unless frozen > 20% revenue) |
| `inventory_stock_concentration` | L1 | **L2** (unless > 70% AND top SKU is revenue driver) |
| `inventory_risk_high` | L1 | **L2** (unless dead_stock ≥ 3 OR OOS on top SKU) |
| `inventory_dead_stock` | L1 | **L1** (keep — actionable) |
| `inventory_slow_movers` | L1 | **L2** |
| `sales_top_sku` | L2 | **L1** (keep revenue primary on pilot) |

**Правило:** Inventory L1 только при **direct revenue impact** (OOS on top SKU, dead stock on A-SKU). Иначе — L2.

### 3. Требуется ли корректировка Executive Summary?

**Да.**

| Проблема | Рекомендация |
|----------|--------------|
| Title = inventory | Title = **best L1 non-inventory** OR highest-IQ insight |
| 3–5 duplicate inventory blocks | **Deduplicate** inventory in `collect_structured_insights` |
| Revenue demoted to slot #3 | **Guarantee** revenue/profit in lead #1–#2 when L1 revenue exists |
| Usefulness = primary IQ only | Consider `max(IQ) among lead[:3]` OR weighted blend |

### 4. Требуется ли изменение Inventory weighting?

**Нет изменений Coverage Engine V1** (по ТЗ 6.3.0).

**Да — изменение Insight Priority weighting:**
- Inventory findings не должны автоматически получать L1 только потому что данные появились
- Severity-based: `high` inventory → L2 default, L1 only with revenue correlation
- Не добавлять inventory deep bullets как отдельные L1 structured insights (double-count)

### 5. Конкретный план исправления (Phase 6.3.0B)

| # | Изменение | Файл | Effort | Impact |
|---|-----------|------|--------|--------|
| 1 | Inventory findings → **L2 default**, L1 conditional on severity + revenue link | `priority_engine.py` | Low | **Usefulness +5–6** |
| 2 | `pick_executive_lead`: primary = **max(IQ) among domain-diverse lead**, not first L1 inventory | `priority_engine.py` | Low | **Usefulness +3–5** |
| 3 | Deduplicate inventory structured insights (analyst + deep bullets) | `composer.py` / `collect_structured_insights` | Low | Clarity ↑ |
| 4 | `seller_usefulness`: `max(IQ × 0.88)` over **lead[:3]**, not only lead[0] | `seller_intelligence.py` | Medium | **Usefulness +4–6** |
| 5 | Improve inventory `why` text with causal markers (SKU, %, period delta) | `priority_engine.py` `_why_from_finding` | Low | IQ +5–8 |
| 6 | Conditional L1: `inventory_*` → L1 only if `frozen_capital_share > 20%` OR `dead_stock ≥ 3` | `inventory.py` severity rules | Low | Precision ↑ |

**Expected outcome после 6.3.0B:**

| Metric | Current | Target |
|--------|---------|--------|
| Seller Usefulness | 68.2 | **≥ 74** (restore baseline) |
| Inventory Insight Rate | 100% | **≥ 50%** (in lead, not necessarily primary) |
| Primary domain mix | 100% Inventory | **≤ 40% Inventory** on pilot |

---

## 7. Appendix — Mechanism reference

### Priority assignment (Phase 6.3.0)

```python
# priority_engine.py — inventory added to L1
_L1_FINDING_PREFIXES = (..., "inventory_dead_stock", "inventory_frozen_capital", ...)
```

### Usefulness boost (unchanged since 6.2.2)

```python
# seller_intelligence.py
boosted = max(coverage_base, insight_quality["overall"] * 0.88)
```

### Insight Quality — causal_depth sensitivity

```python
# quality.py — causal_depth max 25
# Requires _has_causal_analysis(what + why) for +13
# Inventory why often scores only +12 (why present but no causal markers)
```

---

*Аудит выполнен без изменений production-кода. Данные: phase_622/630 audit JSON + 4 AIRecommendation в БД pilot user.*

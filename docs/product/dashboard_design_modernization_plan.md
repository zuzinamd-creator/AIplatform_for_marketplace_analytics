# Dashboard Design Modernization Plan

**Phase:** 9.18-R5 → **R6-P0 implementation (visual layer)**  
**Status:** Palette + hierarchy **APPROVED** · P0 (+ items 5–7) **IMPLEMENTED** · staging `:8443` · **prod not deployed**  
**Warning AA note:** light `warn` adjusted `#B86E00` → `#9A5A00` for soft-surface text ≥4.5:1.  
**Baseline evidence:** `docs/release/screenshots/phase-9.18-r4/`  
**Comparables:** Stripe Dashboard · Linear · Vercel Analytics · Amplitude · Mixpanel · Power BI · Looker Studio  

### Approved core palette

| Role | HEX |
|------|-----|
| Action/Brand | `#0B6BCB` |
| Profit | `#0F7B5A` |
| Expense/Total | `#3D4A5C` |
| Risk | `#C81E1E` |
| Warning | `#9A5A00` (AA on warnSoft; was `#B86E00`) |
| Neutral-900/700/500/300/100 | `#111827` / `#3F4B5A` / `#6B7280` / `#D1D5DB` / `#F3F4F6` |

**Hierarchy:** Primary Answer → Action tasks → Top SKU → Charts.  
**Forbidden:** purple in charts · brand-blue as categorical fill · gradient on Primary Answer.

### Approved P0 scope (implementation)

1. Daily costs on-bar labels + legend honesty (no mismatched color strip)  
2. Chrome diet (one title path; Primary earlier)  
3. Trust once (badge under Primary; omit Action trust-blocker)  
4. Apply core + neutral tokens (+ dark variants) on Overview visual layer  
5. Chart anti-pattern lint (no PieChart, dual-axis `yAxisId`, 3D)  
6. Explicit Trust badge/line contract (`TRUST_BADGE_SPEC`)  
7. Dark-mode tokens in CSS variables (not a later phase)  

P1+ (task-row CTAs, typography brand, etc.) **not in this change**.

### P1 backlog (explicit — not in P0)

**Desktop Primary Answer still ~599px from top (staging live, 1440×900).**  
Problem statement: «чек-лист Первый запуск + period selector съедают fold» — after chrome diet (dual H1 removed) PA moved up (~845→599) but remains below executive fold. Address in next phase (collapse/dismiss checklist; denser period chrome), not this P0.

---

## 1. Текущие проблемы

### 1.1 Системный диагноз

Продукт уже имеет **правильную информационную архитектуру F2** (Primary Answer → Action Strip → Top SKU → charts), но **визуальная система осталась на уровне admin MVP**:

| Слой | Сейчас | Эффект для CEO |
|------|--------|----------------|
| Chrome | Два H1 («Аналитика» + «Финансовая аналитика продавца») + Trust banner + tabs + period | Primary Answer на ~555px — ответ бизнеса **ниже fold** |
| Color | ~25+ hex в UI+charts без единой семантики | Радуга категорий расходов; gray daily bars рядом с цветным strip |
| Type | Только Inter | Нет display-иерархии как у Stripe/Linear |
| Density | Карточки-тексты, link-CTA | Не «задачи руководителя», а help-center |
| Charts | Неравный стандарт подписей | Выручка/структура — labels; **Затраты по дням — только оси** |

### 1.2 Цветовая система сегодня (инвентарь)

**Surfaces (4):** `#ffffff` · `#f4f6f9` · `#e8ecf2` · `#f8fafc`  
**Ink (4):** `#0f172a` · `#334155` · `#64748b` · `#94a3b8`  
**Brand (4):** `#2563eb` · `#1d4ed8` · `#dbeafe` · `#eff6ff`  
**Semantic (8):** success `#047857` / bg `#ecfdf5` · warn `#b45309` / `#fffbeb` · danger `#b91c1c` / `#fef2f2` · info `#0369a1` / `#f0f9ff`  
**Chart series (14+):** revenue `#3b82f6` · profit `#059669` · logistics `#ca8a04` · ads `#7c3aed` · returns `#e11d48` · payout `#4f46e5` · commission `#0d9488` · storage `#d97706` · penalties `#dc2626` · deductions `#9333ea` · acquiring `#2563eb` · other `#64748b` · costTotal `#475569` · …

**Итого уникальных hex в токенах: ~30+.**  
Для executive BI это слишком много; у Stripe/Linear рабочий UI держится на **1 brand + 3–4 semantic + 1 нейтральный ряд**.

### 1.3 Нарушения семантики цвета

| Где | Проблема |
|-----|----------|
| Primary Answer | Gradient `brand-subtle` — бренд как декор «hero», не как действие |
| Ads / deductions charts | Фиолетовый `#7c3aed` / `#9333ea` — декоративная радуга, не смысл |
| Acquiring | Тот же `#2563eb`, что brand CTA — категория = действие |
| Daily costs bars | `#475569` mono, а strip под графиком — цветные категории → **легенда врёт** |
| Profit vs expense | Прибыль emerald OK; расходы размазаны по 9 hue без шкалы «тяжести» |
| Trust chip danger | Семантика верная, но дублируется Action Card тем же текстом |

### 1.4 Иерархия (факт с production)

1. Баннер «Всё стабильно»  
2. H1 «Аналитика» + subtitle  
3. Tabs  
4. H1 «Финансовая аналитика продавца»  
5. Period selector  
6. **Primary Answer** ← должен быть №1  
7. Action Strip  
8. Top SKU  

Для владельца с оборотом 50–100 млн ₽/мес это читается как **внутренняя админка**, не как cockpit.

---

## 2. Лучшие практики рынка

| Паттерн | Stripe / Linear / Vercel | Amplitude / Mixpanel | Power BI / Looker | Применить у нас |
|---------|--------------------------|----------------------|-------------------|-----------------|
| First paint | Один главный metric | One big number + spark | KPI strip pinned | **Один Primary Answer в первые 320–400px** |
| Color | 1 accent; data colors restrained | Diverging for +/- | Theme + field colors | **Brand = action only; data = semantic scale** |
| Actions | Task rows with severity | Alerts with CTA button | Bookmarks | **Action = left rail + button, не link** |
| Charts | Labels when ≤N points; tooltip always | Consistent series colors | Explicit legends matching marks | **Единый Chart Label Standard** |
| Chrome | Minimal page chrome | App shell quiet | Report title once | **Один title на Overview** |
| Trust / quality | Inline badge on metric | Data quality chip | Refresh indicator | **Trust только на Primary Answer** |

**Антипаттерны, которых избегать:** purple-indigo «AI SaaS» клише; cream+terracotta; newspaper dense grids; glow/neon.

---

## 3. Новая дизайн-система (принципы)

Имя рабочей системы: **Ledger UI** (деньги, доверие, действие).

1. **Answer first** — первый экран отвечает: *сколько заработали / сколько осталось / что сделать*.  
2. **Color = meaning** — цвет не украшает карточку; кодирует прибыль / расход / риск / действие.  
3. **One accent** — brand используется для CTA и active nav, не для fills графиков.  
4. **Chart honesty** — цвет серии = цвет в легенде; нет «серых баров + цветной strip».  
5. **Executive density** — меньше chrome, больше сигнала; whitespace Stripe-like, не «пустой MVP».  
6. **Type hierarchy** — display для Primary numbers; UI sans для chrome.  
7. **Motion sparse** — 2–3 осмысленных transition (period change, strip appear), без декора.

### 3.1 Типографика (предложение)

| Role | Font | Size / weight |
|------|------|----------------|
| Brand / product | **Manrope** or **Sora** (geometric, finance-clean) | 13–14 / 600 nav |
| Primary metric | Same family | 36–44 / 600 tabular nums |
| Section title | Same | 15–16 / 600 |
| Body / chart | Same | 13–14 / 400–500 |
| Meta | Same | 12 / 500 muted |

*Не Inter как единственный голос.* Tabular lining figures обязательны для ₽.

### 3.2 Surface & elevation

| Token | HEX | Use |
|-------|-----|-----|
| `canvas` | `#F7F8FA` | Page background (чуть теплее текущего `#f4f6f9`, меньше «больница») |
| `panel` | `#FFFFFF` | Cards |
| `panel-raised` | `#FFFFFF` + shadow `0 1px 2px rgb(15 23 42 / 0.04), 0 8px 24px rgb(15 23 42 / 0.06)` | Primary Answer only |
| `hairline` | `#E6E8EC` | Borders (сильнее нынешних 0.9 opacity) |
| `inset` | `#F1F3F5` | Period bar, nav active soft |

---

## 4. Новая цветовая палитра (конкретные HEX)

### 4.1 Core (обязательные)

| Роль | Token | HEX | Обоснование |
|------|-------|-----|-------------|
| **Бренд / действие** | `action` | `#0B6BCB` | Спокойный «finance blue» (ближе Stripe action, не electric `#2563eb`); только CTA, links, active nav |
| **Бренд hover** | `action-hover` | `#0958A8` | |
| **Бренд soft** | `action-soft` | `#E8F2FC` | Active nav / focus rings |
| **Прибыль** | `profit` | `#0F7B5A` | Глубже `#059669` — читается как money, не «startup green» |
| **Прибыль soft** | `profit-soft` | `#E6F5EF` | Positive chips |
| **Расход (neutral total)** | `expense` | `#3D4A5C` | Единый тон «затраты» для daily totals (вместо серого slate без семантики) |
| **Расход soft** | `expense-soft` | `#EEF1F4` | |
| **Риск** | `risk` | `#C81E1E` | Returns, blockers, insufficient trust |
| **Риск soft** | `risk-soft` | `#FDECEC` | |
| **Предупреждение** | `warn` | `#B86E00` | Partial trust, stale |
| **Предупреждение soft** | `warn-soft` | `#FFF6E5` | |
| **Ink** | `ink` | `#111827` | Primary text |
| **Ink secondary** | `ink-2` | `#3F4B5A` | Axis, secondary |
| **Ink muted** | `ink-3` | `#6B7280` | Meta |

### 4.2 Categorical costs (максимум 6 видимых + other)

Ограничить «радугу». Порядок = бизнес-смысл (доля / внимание), не rainbow:

| Категория | HEX | Почему |
|-----------|-----|--------|
| Комиссия | `#0F766E` | Teal — «плата площадке» |
| Логистика | `#A16207` | Amber — операционный объём |
| Продвижение | `#1D4E89` | Deep blue — инвестиции в спрос (не purple) |
| Возвраты | `#C81E1E` | = risk |
| Хранение | `#7C5E10` | Muted gold |
| Удержания / прочее | `#5B6573` | Neutral slate |
| *(редко)* Штрафы | `#9F1239` | Darker risk |
| *(редко)* Эквайринг | `#334155` | Near expense |

**Запрет:** purple/violet в charts; brand blue как fill категории; gradient на Primary Answer.

### 4.3 Mapping «старое → новое»

| Было | Стало |
|------|-------|
| brand `#2563eb` | action `#0B6BCB` |
| profit `#059669` | profit `#0F7B5A` |
| costTotal `#475569` | expense `#3D4A5C` |
| ads purple | promotion `#1D4E89` |
| Primary gradient brand | flat `panel-raised` + left accent 3px `action` **или** none |

---

## 5. Новая визуальная иерархия

### 5.1 Порядок внимания (desktop first viewport)

| # | Элемент | Задача |
|---|---------|--------|
| 1 | **Primary Answer** (Выручка · Прибыль · Trust chip) | Ответ периода |
| 2 | **Action Strip** (≤3 severity tasks) | Что сделать |
| 3 | **Top SKU** | Где деньги / риск |
| 4 | Revenue trend | Динамика |
| 5 | Cost structure + daily costs | Структура затрат |
| 6 | Financial summary | Детализация |

### 5.2 Что убрать из first viewport

- Дублирующий H1 shell  
- Длинный page subtitle  
- Global «Всё стабильно» (свернуть в status dot в shell)  
- Повтор trust в Action Strip, если chip уже на Primary  

### 5.3 Wireframe (above the fold)

```
┌─ shell (compact) ─────────────────────────────────────┐
│ Nav │  [Period]                    status· · marketplace │
│     │  ┌─ PRIMARY ANSWER ─────────────────────────────┐ │
│     │  │  Выручка 12.4M₽    Прибыль 1.8M₽   [Trust]  │ │
│     │  └──────────────────────────────────────────────┘ │
│     │  ┌ Action ┐ ┌ Action ┐ ┌ Action ┐                 │
│     │  └────────┘ └────────┘ └────────┘                 │
│     │  Top SKU table (compact)                          │
└─────┴───────────────────────────────────────────────────┘
```

---

## 6. План изменений по экранам

| Экран | Изменение |
|-------|-----------|
| **Overview `/app/analytics`** | Убрать второй H1; Primary raised; Actions = task model; charts label standard |
| **Analytics tabs** | Tabs вторичны; Overview без лишнего subtitle |
| **App shell** | Compact nav; product name не «MVP E2E»; status pill вместо banner |
| **Onboarding** | Вне scope R5 visual system, но CTA = те же action tokens |
| **Economics / Weekly** | Наследовать palette + chart standards во 2-й волне |

---

## 7. План изменений по графикам

### Chart Label Standard (единый)

| Правило | Значение |
|---------|----------|
| On-bar / end labels | Обязательны при N ≤ 14 точек (или ≤ 8 категорий) |
| Формат | Compact ₽ (`1.8 тыс.`) или `%` — один тип на график |
| Оси | `ink-2` `#3F4B5A`, 12px |
| Tooltip | Всегда полный ₽ |
| Legend | Только если цвет несёт категорию; цвет legend = цвет mark |

### 7.1 Структура расходов

| Сейчас | Цель |
|--------|------|
| % LabelList OK после R3 | Сохранить |
| Legend дублирует % | Оставить ₽+%; укоротить hints |
| Categorical rainbow | Новая 6-color cost palette |
| Height dynamic | OK |

### 7.2 Затраты по дням — **P0**

| Сейчас | Цель |
|--------|------|
| Нет on-bar labels | **LabelList** compact ₽ (как revenue) |
| Bars `#475569` + цветной strip | Либо **stacked** по top-2 categories + other, либо **убрать strip** и оставить mono `expense` + tooltip breakdown |
| Даты MM-DD | `D MMM` локаль ru при ≤14 дней |
| Пропуски дней | Пунктир / annotation «нет данных» |

### 7.3 Выручка и прибыль

| Сейчас | Цель |
|--------|------|
| Revenue blue / profit green | `action` не использовать; revenue `#3F6F9A` cool slate-blue **или** оставить отдельный `series-revenue #2F6FED` ≠ CTA; profit = `profit` |
| Labels ≤14 | Сохранить; collision → skip small bars |
| Legend | Всегда обе серии, если profit visible |

---

## 8. План изменений по Action Strip

### Сейчас (MVP tells)

- Белые карточки, равный вес  
- CTA = text link 14px  
- Trust дублирует chip  
- Нет severity rail  

### Новая модель: **Executive Task Row**

```
┌─────────────────────────────────────────────┐
│▌ TITLE                         [Secondary]  │  ← 3px left rail: risk|warn|action|neutral
│  One-line body                               │
│  [ Primary button CTA ]                      │
└─────────────────────────────────────────────┘
```

| Severity | Rail HEX | Use |
|----------|----------|-----|
| Blocker | `risk` `#C81E1E` | Нет себестоимости |
| Attention | `warn` `#B86E00` | Returns pressure |
| Opportunity | `action` `#0B6BCB` | Смотреть расходы |
| Neutral | `ink-3` | Empty state |

**Правила:** max 3; не дублировать Trust Chip; CTA = `btn` height 32–36, не link; title ≤ 36 chars.

---

## 9. План изменений по Dashboard (сводка)

1. **Chrome diet** — один title, status pill, period sticky compact.  
2. **Primary Answer** — flat raised card; large tabular ₽; Trust chip once; profit tint when positive (`profit`).  
3. **Action Strip** — task rows + severity.  
4. **Top SKU** — denser table; margin heat via profit/risk soft bgs.  
5. **Charts block** — section label «Динамика» / «Расходы»; apply Chart Label Standard.  
6. **Financial summary** — secondary; collapse by default on mobile.

---

## 10. Приоритеты внедрения

### P0 — Credibility (1 sprint)

1. Daily costs **on-bar labels** + fix strip/bars honesty.  
2. Remove duplicate H1 / bury Primary Answer (chrome diet).  
3. Dedupe trust (chip XOR action card).  
4. Apply core palette tokens (action / profit / expense / risk / warn) to Dashboard + charts.

### P1 — Executive feel (1–2 sprints)

5. Action Strip → task row + button CTA + severity rail.  
6. Primary Answer elevation + type scale.  
7. Cost categorical palette (no purple).  
8. Shell status pill instead of full-width green banner.

### P2 — Brand polish

9. Manrope/Sora + tabular nums.  
10. Top SKU heat + denser executive table.  
11. Motion: period refetch skeleton; strip enter.  
12. Propagate tokens to Weekly / Economics.

---

## 11. Executive UI Review (50–100 млн ₽/мес)

### Будет ли восприниматься как профессиональный продукт?

**Сейчас — частично нет.** Владелец увидит:

- правильные вопросы (выручка / прибыль / действия),  
- но **admin chrome**, **радужные/противоречивые графики**, **text-link задачи**, **ответ ниже fold**.

Это ближе к «внутренняя аналитика команды», чем к Stripe/Triple Whale cockpit.

### Что выдаёт MVP

- Имя «MVP E2E» в shell  
- Два заголовка + «Всё стабильно»  
- Inter everywhere  
- Action cards как help widgets  
- Daily costs без value labels + лживая легенда  
- Purple categories  

### Что уже близко к продукту

- F2 information architecture  
- Trust gating (честность > vanity metrics)  
- Cost structure % after R3  
- Clear Russian copy on actions  

### Вердикт для утверждения

**Рекомендация:** утвердить **Ledger UI** palette + hierarchy + P0/P1 scope выше, затем отдельный implementation phase (например 9.18-R6).  
Без P0 владелец с крупным оборотом продолжит читать продукт как MVP, даже при корректных цифрах.

---

## 12. Примеры экранов (целевые описания для согласования)

### A. Overview — first viewport
- Period compact top-right  
- Primary Answer full width: 2 metrics + trust  
- 3 task cards with rail + filled CTA  
- Top SKU starts at ~fold  

### B. Costs section
- Horizontal structure: teal/amber cats + %  
- Daily: expense bars **with ₽ labels**; tooltip shows breakdown; **no mismatched color strip** (or true stacked)  

### C. Mobile
- Primary stacked  
- Actions vertical severity list  
- Charts full-bleed; labels only if N ≤ 7 else tooltip-first  

---

## Approval checklist

- [ ] Утвердить HEX core palette (action / profit / expense / risk / warn)  
- [ ] Утвердить hierarchy (Primary → Actions → Top SKU)  
- [ ] Утвердить Chart Label Standard + daily costs P0  
- [ ] Утвердить Action = task row (не link cards)  
- [ ] Утвердить P0/P1/P2 порядок  
- [ ] Разрешить implementation phase  

**Статус документа:** готово к утверждению · код не менялся.

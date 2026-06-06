# Платформа аналитики маркетплейсов (WB / Ozon)

Проект: детерминированная финансовая и складская аналитика для продавцов (Wildberries / Ozon) + seller-facing продуктовый интерфейс.

Ключевые принципы (не меняем):

- **Append-only ledger** (финансовый и складской леджер не переписываются).
- **Governed проекции** (агрегаты/снапшоты пересчитываемы, но не “истина”).
- **RLS (Row Level Security)** — строгая tenant-изоляция на уровне PostgreSQL.
- **ИИ только advisory** — ИИ не мутирует источники правды; при деградации данных снижает уверенность.

## Документация (RU)

- Архитектурные инварианты: `docs/architecture/invariants.md`
- Аналитика и целостность: `docs/analytics/financial_semantics.md`, `docs/analytics/integrity_validation.md`, `docs/analytics/report_coverage.md`
- Экономика и прибыльность:
  - `docs/economics/sku_unit_economics.md`
  - `docs/economics/sku_drilldown.md`
  - `docs/economics/inventory_economics_ui.md`
  - `docs/economics/profitability_visualization.md`
- Продуктовые сценарии:
  - `docs/product/economics_workspace.md`
  - `docs/product/seller_profitability_workflows.md`
  - `docs/product/trust_experience.md`
  - `docs/product/daily_workflows.md`
  - `docs/product/upload_diagnostics.md`
  - `docs/product/trust_and_limitations.md`
  - `docs/product/local_deployment.md`
  - `docs/product/local_operations.md`

## ETL-воркер и очередь (production)

Архитектура обработки WB-отчётов (без изменения схемы БД):

| Компонент | Назначение |
|-----------|------------|
| `app/etl/worker.py` | Claim → parse → phased persist → ack; heartbeat на весь job |
| `app/etl/wb/stream_pipeline.py` | Потоковый parse + phase-1 по чанкам (`.xlsx`/`.csv`) |
| `app/etl/wb/persist.py` | 3 фазы: ledger → inventory/reconciliation → aggregates |
| `app/core/queue/postgres_backend.py` | `SKIP LOCKED` очередь `etl_jobs`, fair claim по `file_size_bytes` |

**Память:** файлы материализуются на диск (`report_materialize`), парсинг — `openpyxl` read_only; полный список `normalized_rows` в RAM не держится.

**Graceful shutdown (SIGTERM/SIGINT):** текущий чанк дочитывается и коммитится, следующий не стартует; job уходит в retry (идемпотентные `ON CONFLICT`).

**Retry и backoff:** при ошибке (в т.ч. `lock_timeout` на фазе 3) job → `PENDING`, но не claimable до `processing_started_at` (экспоненциальная задержка, база `JOB_RETRY_BASE_DELAY_SECONDS`, по умолчанию 30s). В логах: `retry_reason`, `attempt`, `retry_eligible_at` (`job_failed_will_retry`, `etl_job_requeued_with_backoff`).

**Фаза 3 (агрегаты):** пересчёт по **полному леджеру за затронутые даты**; SKU-метрики за период сначала удаляются, затем UPSERT; day-level — `ON CONFLICT DO UPDATE`. `SET LOCAL lock_timeout` (`ETL_AGGREGATE_LOCK_TIMEOUT_MS`) снижает риск зависания при конкуренции воркеров.

**Legacy `.xls`:** лимит 50MB в `read_report_file`; при превышении — понятная ошибка с просьбой конвертировать в `.xlsx`.

**Stale jobs:** восстановление по heartbeat (не только `claimed_at`); см. `docs/PR_P0_ETL_STABILIZATION.md`.

Переменные окружения (фрагмент):

- `WORKER_HEARTBEAT_INTERVAL_SECONDS` — интервал heartbeat (default 15)
- `JOB_RETRY_BASE_DELAY_SECONDS` — база exponential backoff (default 30)
- `ETL_AGGREGATE_LOCK_TIMEOUT_MS` — lock timeout фазы 3 (default 5000)
- `JOB_MAX_ATTEMPTS`, `JOB_VISIBILITY_TIMEOUT_SECONDS`

### WB upload: распознавание формата (2026-06)

Потоковый парсер (`app/parsers/wb/header_detection.py`, `streaming.py`) автоматически:

- сканирует **все листы** книги (не только active sheet);
- находит строку заголовков по сигнатурам колонок WB (RU/EN);
- пропускает титульные/пустые строки перед заголовком;
- согласован с pandas-валидацией при upload (`load_wb_dataframe`).

Типовые причины ложной ошибки «Report file contains no data rows» (исправлено):

| Причина | Было | Стало |
|---------|------|-------|
| Данные на неактивном листе | 0 строк | выбирается лист с WB-заголовком |
| Титульные строки перед заголовком | неверный header | header detection |
| «Дата заказа» вместо «Дата продажи» | неверный период | scoring в `resolve_column_map` |

Тесты: `tests/unit/test_wb_header_detection.py`.

### Удаление отчётов

`DELETE /api/v1/reports/{report_id}` — tenant-safe удаление:

- каскад FK: `raw_reports`, `normalized_report_rows`, `financial_ledger_entries`, `inventory_ledger_entries`, `etl_jobs`, …;
- пересчёт `daily_aggregates`, `sku_daily_metrics`, `sku_unit_economics_daily` за затронутые даты;
- rebuild inventory snapshots;
- удаление файла из object storage;
- `cost_history.source_report_id` → NULL (не удаляет себестоимость).

Сервис: `app/services/report_deletion_service.py`.

### KPI и «Покрытие себестоимостью»

- **Чистая прибыль** на dashboard = `daily_aggregates.net_profit` (ledger − COGS). Без загруженной себестоимости маржа ~90% отражает только комиссию WB, не реальную экономику SKU.
- **Покрытие себестoимостью** (`GET /analytics/cost-coverage`) = `SKU с COGS / SKU с продажами × 100%`. Это метрика полноты данных, не «покрытие затрат» в смысле P&L.
- Dashboard показывает предупреждение при `sku_cost_coverage_pct < 100%`.

Проверка tenant isolation: `scripts/rls_leak_test.py` (RLS + FORCE на 35 таблицах, роль `marketplace_app`).

## Что умеет система

- Детерминированная финансовая аналитика по периодам (выручка/прибыль/маржа/возвраты/выплаты).
- Экономика SKU (таблица прибыльности + drilldown).
- Складская экономика (оборот, замороженный капитал, slow movers, dead stock).
- Сверка выплат: “почему выплата ≠ прибыль”.
- AI advisory‑рекомендации с прозрачностью confidence/evidence/limitations.
- Персистентный workflow продавца: заметки, напоминания, история действий.

## Что НЕ умеет система (важно)

- Не делает прогнозирование ML (нет forecasting “по модели”).
- ИИ не выполняет действий на маркетплейсе и не меняет источники правды.
- Не гарантирует точность прибыли без себестоимости и при неполных отчётах.

## Как работает AI (коротко)

- AI получает **только governed данные** (агрегаты/снапшоты/интегрити‑сигналы).
- Возвращает advisory‑рекомендации с:
  - confidence
  - evidence refs
  - limitations
  - пояснением “почему AI может ошибаться”

## Как работает финансовая модель (коротко)

- **Profit ≠ payout**: выплата — денежный поток, прибыль — P&L.
- Деньги считаются Decimal‑only.
- Источник правды: append‑only ledger; проекции пересчитываемы.

## Команды для ежедневного локального запуска (MANDATORY)

### Windows (PowerShell) — “с утра”

Backend:

```powershell
Set-Location "C:\path\to\AIplatform_for_marketplace_analytics"
.\.venv\Scripts\activate
alembic upgrade head
uvicorn app.main:app --reload
```

Worker (в отдельном терминале):

```powershell
Set-Location "C:\path\to\AIplatform_for_marketplace_analytics"
.\.venv\Scripts\activate
python -m app.etl.worker
```

Orchestrator (опционально, в отдельном терминале):

```powershell
Set-Location "C:\path\to\AIplatform_for_marketplace_analytics"
.\.venv\Scripts\activate
python -m app.runtime.orchestration_worker
```

Frontend:

```powershell
Set-Location "C:\path\to\AIplatform_for_marketplace_analytics\frontend"
npm install
npm run dev
```

### Docker (опционально)

```powershell
Set-Location "C:\path\to\AIplatform_for_marketplace_analytics"
copy .env.example .env
docker compose up --build
```

## Загрузка отчётов (UX)

- UI: `/app/reports/upload`
- Список: `/app/reports` — только отчёты текущего пользователя (RLS + `user_id`), до **200** последних загрузок.
- Колонки **«Период»** (`period_start` / `period_end`): даты «с» и «по» из проводок после ETL; до обработки — «—».
- После загрузки смотрите подсказки “Что нужно загрузить…” (coverage‑driven).

## Себестоимость (UX)

- UI: `/app/costs` — таблица загруженных строк (не JSON).
- Режим **«На дату»** (`GET /api/v1/costs?as_of=YYYY-MM-DD`) — актуальная себестоимость по SKU на выбранный день.
- **Ручное редактирование** ячеек сумм: `PATCH /api/v1/costs/{id}` (клик по ячейке в таблице).
- Импорт: шаблон Excel + `POST /api/v1/costs/import/v2`.

## Production frontend (VPS без Docker)

На сервере UI отдаёт **nginx** из `/var/www/marketplace-analytics` (не Vite dev).  
На VPS с 2 GB RAM **отключите** опциональный preview: `sudo systemctl disable --now marketplace-frontend.service`.

**Деплой одной командой** (остановка preview, очистка Node, проверка RAM, лимит heap 1 GB):

```bash
cd /root/AIplatform_for_marketplace_analytics && bash scripts/deploy-frontend.sh
```

Первичная установка systemd + ежедневная очистка npm/vite: `sudo bash scripts/install-frontend-ops.sh`  
Подробнее: `docs/ops/frontend-deploy.md`

При изменениях API: `sudo systemctl restart marketplace-backend`

Проверка: `curl -s http://127.0.0.1/ | grep surface-muted` — в HTML должна быть светлая тема (`bg-surface-muted`), не `slate-950`.

## AI анализ

- UI: `/app/dashboard` → “ИИ-анализ периода”
- UI: `/app/ai/recommendations` / детали рекомендации (trust + limitations + история действий)

## Типовые workflow продавца

См. `docs/product/daily_workflows.md`.

## Ограничения системы

- Качество экономических метрик зависит от:
  - покрытия себестоимости
  - полноты периодов
  - корректности импортированных отчётов

## Production risks (даже локально)

- Неполная себестоимость → искаженная прибыль/маржа/замороженный капитал.
- Пропуски периодов → неправильные тренды/сравнения.
- Stale rebuild/очередь → данные могут быть не “как сейчас”.
- Несколько `marketplace-worker` на одной БД → конкуренция на фазе 3; ожидайте `lock_timeout` + backoff, не бесконечный spin.
- Прерванный streaming-job (shutdown) → retry с уже записанными чанками phase-1 (безопасно за счёт idempotency).

## Полная карта API (коротко)

Префикс: `/api/v1`

- Auth: `/auth/*`
- Reports: `/reports/*`
- Costs: `/costs/*`
- Analytics: `/analytics/*`
- AI: `/ai/*`
- Workflow: `/workflow/*`

## Seller UX: маршруты (frontend)

- `/app/dashboard` — панель продавца (период, доверие к данным, ключевые KPI)
- `/app/economics` — **Экономика SKU** (таблица прибыльности, сравнение периодов, мини-тренды)
- `/app/economics/sku/:sku` — **Drilldown SKU** (почему убыточен, что ухудшилось, тренды)
- `/app/economics/inventory` — **Склад и оборот** (замороженный капитал, slow movers, dead stock)
- `/app/finance/costs` — покрытие себестоимости (cost coverage)
- `/app/finance/reconciliation` — сверка выплат (payout ≠ profit)
- `/app/today` — “что требует внимания сегодня”

## API: экономика и склад (backend)

Экономика SKU:

- `GET /api/v1/analytics/sku-economics`
- `GET /api/v1/analytics/sku-economics/sku/{sku}/drilldown`

Складская экономика:

- `GET /api/v1/analytics/inventory-economics`
- `GET /api/v1/analytics/inventory-economics/slow-movers`
- `GET /api/v1/analytics/inventory-economics/dead-stock`

Доверие к данным (показывать в UI всегда):

- `freshness` (data-as-of, rebuild/queue, stale/degraded)
- `integrity.warnings[]`
- `financial_completeness_score` (best-effort 0..100)

## Локальный запуск (Windows)

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Валидация (обязательная)

Если видите `No module named pytest`, запускайте тесты через интерпретатор виртуального окружения:

```powershell
.\.venv\Scripts\python -m pytest tests/unit -q
$env:RUN_INTEGRATION_TESTS="true"
.\.venv\Scripts\python -m pytest tests/integration/test_phase3_aggregate_contention.py -v
.\.venv\Scripts\python -m pytest tests/integration -m integration
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m mypy app tests
```

Frontend build:

```powershell
cd frontend
npm run build
```

## Интеграционное тестирование (локально, без skip)

### Env профиль

Файл: `.env.integration`

Ключевые переменные:

- `RUN_INTEGRATION_TESTS=true`
- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test`
- `TEST_AI_PROVIDER=mock`

### Docker integration profile

```powershell
# поднять окружение (Postgres + migrate + api + worker + frontend)
.\scripts\integration-up.ps1
```

Сервисы:

- Postgres: `localhost:5434` (DB: `marketplace_test`)
- API+nginx: `http://localhost:8081`
- Frontend: `http://localhost:5173`

Сброс окружения:

```powershell
.\scripts\integration-reset.ps1
```

### Запуск integration tests

```powershell
.\scripts\integration-test.ps1
```

### Bootstrap E2E сценарий

Скрипт загрузит тестовый `.xlsx` из `tests/*.xlsx`, проверит API, и запустит AI‑анализ периода (mock):

```powershell
.\.venv\Scripts\python scripts\bootstrap_integration_data.py
```

## Локализация интерфейса

Цель: **полная seller-facing русификация** (без перевода кода/схем API/внутренних dev-инструментов).

Правила:

- Переводим только то, что видит продавец: кнопки, лейблы, плейсхолдеры, empty states, onboarding, тексты AI, предупреждения доверия.
- Не переводим: внутренние технические страницы/операторские экраны, dev tooling, имена полей API и схемы.
- Терминология должна быть единой (например: Выручка / Прибыль / Маржинальность / Полнота данных / Достоверность / Рекомендация).

Структура:

- Централизованные строки: `frontend/src/i18n/ru.ts`
- Простой helper: `frontend/src/i18n/index.ts` (`t("...")`)

## Импорт себестоимости

### Где скачать шаблон

- UI: `/app/costs` → **«Скачать шаблон для заполнения»**
- API: `GET /api/v1/costs/import/template`

Шаблон берётся из сервера по детерминированному приоритету:

1. `app/resources/cost_template.xlsx` (production template)
2. `app/resources/Шаблон Себестоимости.xlsx`
3. `app/resources/cost_import_template.xlsx` (fallback)

Проверка выбора шаблона (для диагностики):

```powershell
curl http://localhost:8080/api/v1/costs/import/template-info -H "Authorization: Bearer <token>"
```

### Поддерживаемые колонки (aliases)

Обязательные:

- `SKU` / `internal_sku` / `артикул` / `артикул поставщика`
- `Дата` / `effective_from` / `date`
- `Себестоимость` / `product_cost` / `cost`

Опционально:

- `Упаковка` / `packaging_cost`
- `Логистика` / `inbound_logistics_cost`
- `Доп.` / `additional_cost`
- `Валюта` / `currency` (например `RUB`)
- `Комментарий` / `comment`

### Ежедневный workflow продавца

1) Обновили закупочные цены → загрузили файл в `/app/costs`  
2) Проверили превью и предупреждения  
3) Импортировали → обновили `/app/finance/costs` (покрытие) и `/app/economics` (прибыльность)  

### Troubleshooting

- **Шаблон не скачивается / 404**: проверьте, что один из файлов шаблона реально лежит в `app/resources/`.
- **Много пропусков при импорте**: чаще всего это пустой SKU, некорректная дата или себестоимость \(<= 0\).
- **Дубликаты**: строки с одинаковыми \(SKU + дата + сумма\) детектируются и пропускаются.

## Сохранность данных (важно)

Отчёты и себестоимость **не хранятся в браузере** — они в PostgreSQL и привязаны к вашему аккаунту (RLS).

Чтобы при входе “всегда открывался ваш кабинет с ранее загруженными данными”, нужно:

- **Использовать одно и то же backend‑окружение** (тот же `VITE_API_BASE_URL` / тот же сервер).
- **Использовать одну и ту же БД** на сервере (одна `DATABASE_URL` для прод‑окружения).
- **Не удалять volume Postgres**, если это рабочие данные:
  - команда `docker compose down -v` удаляет тома и очищает БД.

Отдельно: integration‑окружение (`docker-compose.integration.yml`) предназначено для тестов и может сбрасываться.

## Архитектура хранения данных (centralized SaaS-ready)

### Режимы окружений

Система работает в одном из режимов (`ENVIRONMENT_MODE`):

- `LOCAL_DEV`: локальная разработка (может быть ephemeral, если Postgres на localhost/docker).
- `INTEGRATION`: тестовое окружение (данные могут удаляться reset’ом, отдельная БД).
- `MAIN`: основное рабочее окружение (должно использовать **persistent cloud DB**).

### Какие окружения считаются ephemeral

Если `DATABASE_URL` указывает на `localhost` / `127.0.0.1` / docker‑host (`postgres`), окружение считается **ephemeral**:
данные могут “пропасть” при `down -v`, пересоздании тома или при переключении окружения.

### MAIN (Supabase PostgreSQL + Supabase Storage)

Централизованное persistent‑хранилище: одна БД и один bucket для всех сессий (локальный браузер — только UI).

Обязательные переменные (см. `.env.example`):

- `ENVIRONMENT_MODE=MAIN`
- `DATABASE_URL=postgresql+asyncpg://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres?ssl=require` (direct connection)
- `STORAGE_BACKEND=supabase`
- `ALLOW_LOCAL_STORAGE_FALLBACK=false`
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_STORAGE_BUCKET`

При старте API проверяется: не ephemeral host, SSL в URL, без local storage fallback в MAIN.

**Миграции (один раз на проект Supabase):**

```bash
# из корня репозитория, с загруженным .env (MAIN)
alembic upgrade head
```

**Запуск backend (хост, без Docker):**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
# health: GET http://localhost:8000/health
# persistence: GET /api/v1/system/persistence-status (JWT)
```

**Проверка после рестарта:** данные живут в Supabase Postgres/Storage — перезапуск `uvicorn` или контейнера API **не** очищает отчёты. Не используйте `docker compose down -v` на прод‑томах.

**Резервное копирование / безопасность:**

- Включите Point-in-Time Recovery / backups в Supabase Dashboard.
- Не коммитьте `.env`; ротируйте `SECRET_KEY` и service role key.
- Integration‑тесты (`ENVIRONMENT_MODE=INTEGRATION`, порт `5434`) — отдельная БД, не MAIN.

### Supabase direct Postgres SSL (asyncpg)

MAIN использует **direct** host `db.<project-ref>.supabase.co:5432` с полной проверкой TLS через **certifi** (`app/core/asyncpg_connect.py` — общий для API, Alembic, worker).

- `?ssl=require` в `.env` обязателен для startup validation; в engine URL параметр `ssl` убирается — TLS задаётся только в `connect_args["ssl"]`;
- **Важно:** `resolve_database_url()` использует `URL.render_as_string(hide_password=False)` — `str(URL)` маскирует пароль как `***`, из‑за чего asyncpg раньше подключался с неверным паролем;
- при пароле с `@ : / #` задайте `DATABASE_PASSWORD` отдельно или используйте `format_database_url_for_env()` (URL-encoding);
- опционально: `DATABASE_SSL_EXTRA_CA_FILE` (корпоративный CA при SSL inspection).

Требования к `DATABASE_URL` в MAIN:

- обязательно `?ssl=require` (или `sslmode=require`);
- host `db.<project-ref>.supabase.co`, порт `5432`, пользователь `postgres` (из Dashboard → Direct connection).

Проверка подключения:

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe scripts\smoke_db_connect.py
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### INTEGRATION safety (не трогать MAIN)

Интеграционные команды запускаются с отдельным именем проекта docker compose (`-p ma_integration`),
поэтому reset тестов не затрагивает рабочие контейнеры/тома.

### Endpoint контроля сохранности

`GET /api/v1/system/persistence-status` возвращает:

- окружение, host/name БД
- persistent_storage true/false
- счётчики: reports / ledger / ai_runs / workflows
- oldest/newest report

UI показывает окружение/БД в левом меню, чтобы пользователь не попадал “в другое окружение” незаметно.


# Marketplace Analytics Data Platform

Production-grade async FastAPI backend for Wildberries and Ozon marketplace analytics. Wildberries reports are processed as a **financial data platform** (historical storage, ledger, reconciliation, materialized aggregates), not as a one-off Excel parser.

## 1. Project Overview

Multi-tenant SaaS backend with:

- JWT authentication and strict Pydantic v2 API contracts
- PostgreSQL Row Level Security (RLS) on all tenant tables
- Async SQLAlchemy 2.0 + Alembic migrations
- Dedicated ETL worker process and PostgreSQL-backed job queue (`etl_jobs`)
- Object storage abstraction (Supabase primary, local dev fallback)
- **Decimal-only** money calculations in `app/domain/`

## 2. High-Level Architecture

```mermaid
flowchart TB
  Client[Client / Nginx]
  API[FastAPI API]
  PG[(PostgreSQL + RLS)]
  Storage[(Object Storage)]
  Worker[ETL Worker]

  Client --> API
  API --> PG
  API --> Storage
  Worker -->|QueueSession| PG
  Worker -->|TenantSession| PG
  Worker --> Storage
```

| Process | Responsibility |
|---------|----------------|
| **API** | Auth, upload orchestration, read models, cost management |
| **Worker** | Claim jobs, CPU ETL, tenant persist, ack/fail |
| **PostgreSQL** | Historical finance tables, aggregates, queue state |
| **Storage** | Immutable raw report files (checksum-addressed) |

## 2b. Architecture guarantees and invariants

Platform behavior is governed by **explicit system contracts**, not implicit README fragments or test-only assumptions.

| Document | Purpose |
|----------|---------|
| [docs/architecture/invariants.md](docs/architecture/invariants.md) | Normative invariant IDs (ledger, snapshots, queue, semantics, ops, tenant, testing) |
| [docs/architecture/invariant_mapping.md](docs/architecture/invariant_mapping.md) | Invariant → code module → test mapping |
| [docs/architecture/invariant_validation_matrix.md](docs/architecture/invariant_validation_matrix.md) | Coverage gaps, risks, operational impact |

### Invariant summary (non-exhaustive)

- **Ledger:** append-only; deterministic replay order; rebuild never mutates history.
- **Snapshots:** one row per `(date, sku, warehouse)`; atomic staging promote; fingerprint-stable replay.
- **Queue:** `SKIP LOCKED` exclusive claim; bounded retries; visibility recovery; no duplicate processing.
- **Semantics:** no silent fallback; version frozen on rows; invalidation queues rebuild (no inline).
- **Operations:** advisory lock fail-fast; anomaly persist isolated from ledger txn; drift checks read-only.
- **Tenancy:** RLS isolation; per-tenant rebuild locks.

### Runtime probes (log-only)

`app/core/invariants/checks.py` emits `platform_invariant_violation` warnings for draft-batch duplicates, negative unit rollups, unknown semantics in drafts, and staging/live row-count mismatch after promote. **These do not abort transactions** and do not replace DB constraints or integration proofs.

### Operational guarantees

1. Treat [invariants.md](docs/architecture/invariants.md) as the change checklist for any ETL/rebuild/queue work.
2. Add or extend integration tests when introducing a new invariant or changing enforcement.
3. Run stress-gated benchmark (`RUN_STRESS_TESTS`) before claiming scalability changes.
4. Monitor `platform_invariant_violation`, `advisory_lock_contention`, and `inventory_integrity_anomalies` in production logs.

**Why explicit invariants matter:** AI-assisted refactors often “simplify” code by collapsing transactions, adding silent defaults, or skipping locks. Named contracts make violations visible during review and map directly to tests — reducing architectural drift without redesigning production services.

## 2c. Architecture governance

Human-readable controls for long-term evolution (not a runtime governance engine).

| Document | Purpose |
|----------|---------|
| [docs/architecture/adr/](docs/architecture/adr/README.md) | Architecture Decision Records (ADR-001 … ADR-008) |
| [docs/architecture/boundaries.md](docs/architecture/boundaries.md) | Layer, transaction, rebuild, queue, tenancy boundaries |
| [docs/architecture/ai_change_policy.md](docs/architecture/ai_change_policy.md) | What AI/humans may change vs forbidden modifications |
| [docs/architecture/engineering_standards.md](docs/architecture/engineering_standards.md) | LOC, tests, migrations, observability standards |
| [docs/architecture/review_checklist.md](docs/architecture/review_checklist.md) | Pre-merge architecture checklist |

## 2e. Platform consolidation (structure)

Formal map of bounded contexts, ownership, layers, and extension rules — **stabilizes evolution without redesigning algorithms**.

| Document | Purpose |
|----------|---------|
| [docs/architecture/domain_map.md](docs/architecture/domain_map.md) | Bounded contexts, upstream/downstream, anti-corruption, shared kernel |
| [docs/architecture/ownership_model.md](docs/architecture/ownership_model.md) | Authoritative vs derived data, mutation permissions |
| [docs/architecture/platform_layers.md](docs/architecture/platform_layers.md) | API → services → ETL → domain; sync/async; queue/rebuild ownership |
| [docs/architecture/dependency_rules.md](docs/architecture/dependency_rules.md) | Allowed imports, DB patterns, orchestration entrypoints |
| [docs/architecture/extension_contracts.md](docs/architecture/extension_contracts.md) | How to add marketplaces, ETL, AI, analytics, rebuilds, semantics |

### Platform structure overview

```mermaid
flowchart LR
  subgraph clients
    HTTP[API + JWT]
    OPS[Ops read API]
  end
  subgraph orchestration
    SVC[Services]
    ETL[ETL Worker]
    OPSM[Operations recovery]
  end
  subgraph truth
    LED[Append-only ledgers]
    RAW[Raw reports]
  end
  subgraph derived
    SNAP[Snapshots / aggregates]
    DTO[Analytics DTO]
  end

  HTTP --> SVC
  OPS --> SVC
  SVC --> ETL
  ETL --> LED
  ETL --> SNAP
  SNAP --> DTO
  RAW --> ETL
  OPSM -.->|explicit| ETL
```

| Layer | Path | Owns |
|-------|------|------|
| API | `app/api`, `app/schemas` | HTTP, validation, projections |
| Services | `app/services` | Tenant use-cases, enqueue |
| ETL | `app/etl` | Worker, persist, rebuild execution |
| Domain | `app/domain` | Pure ledger/snapshot/analytics math |
| Parsers | `app/parsers` | File → normalized rows |
| Operations | `app/operations` | Recovery, orchestration metadata, safety guards |
| Infrastructure | `app/core`, `app/storage` | RLS sessions, queue, observability |
| Persistence | `app/models`, `alembic` | ORM, migrations |
| AI execution | `app/ai`, `app/dto` | Governed runs; `AIInsightInputDTO` contract |

### Dependency model (summary)

- **Downhill only:** API → services → ETL → domain; parsers feed domain/ETL, never persist.
- **Forbidden:** domain → SQLAlchemy/API/ETL; queue → domain; API → `etl.wb` internals.
- **Legacy warning:** `app/api/reports.py` imports `app.etl.loaders` — do not extend this pattern.
- **Shared kernel:** enums and semantics types may cross domain ↔ models ↔ parsers with ADR discipline.

Full matrix: [dependency_rules.md](docs/architecture/dependency_rules.md).

### Extension model (summary)

| Extension | Contract doc section | Hard requirements |
|-----------|---------------------|-------------------|
| New marketplace | extension_contracts §1 | Parser + ETL + pipeline route + tests |
| New semantics version | §6 | Registry + invalidation + rebuild + ADR-007 |
| New rebuild strategy | §5 | Advisory lock, fingerprint equivalence, stress benchmark |
| New AI module | §3 | Read-only via DTO; no ledger mutation |
| New analytics | §4 | Domain pure functions; Decimal money |

### Architectural fitness functions

```bash
python scripts/architecture_governance_check.py
```

Enforces: required consolidation docs, layer import rules, forbidden patterns (blocking advisory lock, RLS bypass), governed-module test hints, LOC warnings, git-diff ADR/README hints.

## 2f. Runtime automation

Automated rebuild dispatch and supervision — incremental on existing queue/rebuild/recovery (no distributed orchestration framework).

| Document | Purpose |
|----------|---------|
| [docs/runtime/runtime_architecture.md](docs/runtime/runtime_architecture.md) | Processes, dispatch path, session model |
| [docs/runtime/scheduling_model.md](docs/runtime/scheduling_model.md) | Poll schedules, env config, scheduling invariants |
| [docs/runtime/orchestration_lifecycle.md](docs/runtime/orchestration_lifecycle.md) | Rebuild requirement state machine |
| [docs/runtime/retry_model.md](docs/runtime/retry_model.md) | ETL + orchestration retry, poison, escalation |
| [docs/runtime/queue_observability.md](docs/runtime/queue_observability.md) | Structured log events and ops correlation |

### Processes

| Process | Command | Role |
|---------|---------|------|
| ETL worker | `python -m app.etl.worker` | Report jobs: claim → parse → persist → ack |
| Orchestrator | `python -m app.runtime.orchestration_worker` | Rebuild queue: dispatch → full/incremental rebuild |

### Rebuild dispatch (`RebuildDispatcher`)

- Selects eligible rows: priority, fairness (`select_fair_batch`), `next_eligible_at`, `max_attempts`
- Cross-tenant listing: `DispatchSession` (queue_role read)
- Execution: `TenantSession` + `FullInventoryRebuildService` / `InventorySnapshotRebuildService`
- Lock busy: `mark_deferred_lock_busy` (no retry attempt consumed)
- Logs: `runtime_rebuild_dispatched`, `runtime_rebuild_succeeded`, `runtime_rebuild_deferred_busy`

### Retry supervision (`RetrySupervisor`)

Periodic maintenance (orchestrator): stale `running` reset, backoff fill, poison audit logs, sample visibility recovery.

### Scheduling (explicit poll)

| Loop | Default interval |
|------|------------------|
| ETL idle poll | 2s |
| Orchestrator poll | 5s (`ORCHESTRATOR_POLL_INTERVAL_SECONDS`) |
| Maintenance | every 12 cycles (`ORCHESTRATOR_MAINTENANCE_EVERY_CYCLES`) |

### Runtime configuration

| Env | Default | Purpose |
|-----|---------|---------|
| `ORCHESTRATOR_ENABLED` | `true` | Enable dispatch |
| `ORCHESTRATOR_MAX_DISPATCH_PER_CYCLE` | `1` | Bounded concurrency |
| `ORCHESTRATOR_DEFER_BUSY_SECONDS` | `60` | Advisory lock backoff |
| `ORCHESTRATOR_RUNAWAY_REBUILDS_PER_HOUR` | `30` | Runaway warning threshold |

### Operational lifecycle

1. **Semantics invalidation** → `snapshot_rebuild_requirements` row (`pending`)
2. **Orchestrator** → fair select → rebuild under advisory lock
3. **Success** → `succeeded`; **busy** → `deferred`; **error** → `deferred`/`failed` with backoff
4. **Maintenance** → stale running cleanup, queue metrics, recovery samples
5. **Ops** → `/api/v1/ops/rebuilds`, `/ops/queue` (read-only)

### Queue supervision

ETL worker: `recover_stale()` each iteration. Orchestrator: `runtime_queue_metrics`, lag/overload warnings. Explicit recovery: `TenantRecoveryService` (runbooks).

## 2i. Runtime autonomy & control plane (Phase 3)

Lightweight PostgreSQL-centric operational autonomy — no Kubernetes-style orchestration, no hidden retry loops.

| Document | Purpose |
|----------|---------|
| [docs/runtime/control_plane.md](docs/runtime/control_plane.md) | Coordinator, state dimensions, ops APIs |
| [docs/runtime/runtime_lifecycle.md](docs/runtime/runtime_lifecycle.md) | Cycle, rebuild transitions, degraded modes |
| [docs/runtime/operational_policies.md](docs/runtime/operational_policies.md) | Config-driven limits |
| [docs/runtime/runtime_autonomy_report.md](docs/runtime/runtime_autonomy_report.md) | Maturity, risks, scale limits |
| [docs/runtime/autonomy_governance.md](docs/runtime/autonomy_governance.md) | Automate vs human, kill switches |

### Control plane

`python -m app.runtime.orchestration_worker` runs `RuntimeControlPlane.run_cycle()`:

1. Due schedules (maintenance, autonomy, health, metrics)
2. Global health evaluation + overload guards
3. Optional `RebuildDispatcher` dispatch (throttled when overloaded)

### Adaptive rebuild dispatch

- `AdaptiveRebuildPrioritizer` — starvation-aware ordering before `select_fair_batch`
- `RuntimeOperationalPolicy.should_throttle_dispatch` — backlog / queue overload
- Incremental → full when `RUNTIME_INCREMENTAL_TO_FULL_AFTER_ATTEMPTS` reached

### Autonomous recovery (bounded)

`AutonomousHealer` (when `RUNTIME_AUTONOMY_ENABLED`): stale RUNNING reset, tenant defer under queue pressure, stuck job sample recovery. Audit: `runtime_autonomy_events` + `runtime_autonomy_action` metrics. Cap: `RUNTIME_MAX_AUTONOMOUS_ACTIONS_PER_CYCLE`.

### Health model

`RuntimeHealthEvaluator` dimensions: queue, rebuild, AI execution. Severity: `ok` / `warn` / `critical`. Tenant ops: `GET /api/v1/ops/runtime/health`, `GET /api/v1/ops/runtime/summary`.

### Scheduling

In-process `ScheduleRegistry` (poll-aligned). Kinds: maintenance, autonomy, health, queue visibility. See [scheduling_model.md](docs/runtime/scheduling_model.md).

### Runtime configuration (Phase 3)

| Env | Default | Purpose |
|-----|---------|---------|
| `RUNTIME_AUTONOMY_ENABLED` | `true` | Master autonomy switch |
| `RUNTIME_MAX_AUTONOMOUS_ACTIONS_PER_CYCLE` | `3` | Self-healing cap |
| `RUNTIME_QUEUE_OVERLOAD_THRESHOLD` | `500` | Dispatch throttle + health |
| `RUNTIME_REBUILD_BACKLOG_WARN` | `50` | Rebuild health WARN |
| `RUNTIME_INCREMENTAL_TO_FULL_AFTER_ATTEMPTS` | `3` | Escalation to full rebuild |
| `RUNTIME_MAX_CONCURRENT_REBUILDS_GLOBAL` | `32` | Running rebuild health |
| `RUNTIME_AI_PAUSE_WHEN_OVERLOADED` | `true` | AI guard when overloaded |

### Migration

`0015_runtime_autonomy_events` — autonomy audit table with RLS.

## 2j. Production reliability (Phase A)

Enterprise hardening — additive layer on runtime control plane. No architecture rewrite.

| Document | Purpose |
|----------|---------|
| [docs/runtime/reliability_model.md](docs/runtime/reliability_model.md) | Layers, invariants, config map |
| [docs/runtime/failure_containment.md](docs/runtime/failure_containment.md) | Quarantine, storms, DLQ escalation |
| [docs/runtime/runtime_resilience.md](docs/runtime/runtime_resilience.md) | Heartbeats, leases, shutdown |
| [docs/runtime/runtime_event_taxonomy.md](docs/runtime/runtime_event_taxonomy.md) | Structured events + tracing |
| [docs/runtime/production_readiness.md](docs/runtime/production_readiness.md) | Go-live checklist, authority |
| [docs/runtime/maintenance_mode.md](docs/runtime/maintenance_mode.md) | MAINTENANCE_MODE semantics |
| [docs/runtime/autonomous_operations.md](docs/runtime/autonomous_operations.md) | Phase C autonomous engine |
| [docs/runtime/scheduling_model.md](docs/runtime/scheduling_model.md) | Enterprise scheduling |
| [docs/runtime/self_healing.md](docs/runtime/self_healing.md) | Self-healing flows |
| [docs/runtime/autonomous_governance.md](docs/runtime/autonomous_governance.md) | Autonomy boundaries |
| [docs/runtime/operational_forecasting.md](docs/runtime/operational_forecasting.md) | Forecasting model |

### Reliability architecture

```mermaid
flowchart TB
  KS[RuntimeKillSwitches] --> W[ETL Worker]
  KS --> O[Orchestrator]
  KS --> AI[AIAnalyticsEngine]
  CB[CircuitBreakerRegistry] --> RD[RebuildDispatcher]
  CB --> LLM[AI Provider]
  TG[TenantContainmentGuard] --> W
  TG --> RD
  PS[ProcessSupervisor] --> HB[(runtime_process_heartbeats)]
  OL[OrchestratorLease] --> O
  OA[operator_audit_events] --> REC[TenantRecoveryService]
```

### Production guarantees (new)

| Guarantee | Mechanism |
|-----------|-----------|
| Rebuild storm containment | Hourly cap + `rebuild_dispatch` circuit breaker |
| Queue overload protection | Policy throttle + degradation LIMITED |
| Tenant poison isolation | Quarantine on DLQ threshold |
| AI runaway containment | Platform hourly cap + tenant rate limit |
| Orchestrator singleton | PostgreSQL lease `orchestrator_primary` |
| Operator accountability | `operator_audit_events` on DLQ replay |
| Graceful degradation | `DegradationLevel` derived each control-plane cycle |
| Startup safety | `validate_environment()` on API/worker/orchestrator |

### Kill switches & maintenance

| Env | Effect |
|-----|--------|
| `MAINTENANCE_MODE` | Blocks worker claims, dispatch, autonomy |
| `WORKER_ENABLED=false` | ETL worker idle |
| `ORCHESTRATOR_ENABLED=false` | No rebuild dispatch |
| `AI_ENABLED=false` | AI runs rejected |
| `RUNTIME_AUTONOMY_ENABLED=false` | No autonomous healer |

### Reliability configuration

| Env | Default | Purpose |
|-----|---------|---------|
| `RELIABILITY_CIRCUIT_FAILURE_THRESHOLD` | `5` | Breaker open threshold |
| `RELIABILITY_CIRCUIT_RECOVERY_SECONDS` | `60` | Breaker half-open delay |
| `RELIABILITY_ORCHESTRATOR_LEASE_TTL_SECONDS` | `30` | Orchestrator ownership |
| `RELIABILITY_TENANT_QUARANTINE_DLQ_THRESHOLD` | `10` | Tenant quarantine |
| `RELIABILITY_REBUILD_STORM_PER_HOUR` | `40` | Rebuild storm circuit |
| `RELIABILITY_AI_RUNAWAY_PER_HOUR` | `100` | Platform AI cap |
| `AI_FAILOVER_PROVIDER` | `` | Optional secondary LLM provider |

### Migration

`0016_production_reliability` — process heartbeats, orchestrator leases, tenant containment, operator audit.

## 2k. AI operational intelligence (Phase B)

Phase B evolves the advisory AI layer into a **governed decision and recommendation system** — still advisory-first, never mutating authoritative ledgers.

| Document | Purpose |
|----------|---------|
| [docs/ai/decision_engine.md](docs/ai/decision_engine.md) | Scoring, prioritization, risk classification |
| [docs/ai/multi_agent_architecture.md](docs/ai/multi_agent_architecture.md) | Planner → Analyst → Validator → Ops Advisor |
| [docs/ai/explainability.md](docs/ai/explainability.md) | Evidence graph, reasoning traces, provenance |
| [docs/ai/recommendation_governance.md](docs/ai/recommendation_governance.md) | Approval gates, trust model, human override |
| [docs/ai/evaluation_strategy.md](docs/ai/evaluation_strategy.md) | Intelligence eval fixtures and benchmarks |
| [docs/ai/strategic_memory.md](docs/ai/strategic_memory.md) | Long-lived tenant memory, deduplication |

### Architecture (Phase B)

```mermaid
flowchart TB
  API["POST /api/v1/ai/intelligence/runs"] --> IE[AIIntelligenceEngine]
  IE --> AE[AIAnalyticsEngine]
  IE --> MAC[MultiAgentCoordinator]
  MAC --> DE[AIDecisionEngine]
  MAC --> VAL[validate_recommendation]
  MAC --> EXP[build_explainability]
  IE --> GOV[classify_and_gate]
  IE --> REC[(ai_recommendations)]
  IE --> MEM[(ai_strategic_memory)]
  AE -.-x LED[Ledgers / snapshots]
```

| Component | Role |
|-----------|------|
| `AIDecisionEngine` | Priority, revenue opportunity, risk, approval gates |
| `MultiAgentCoordinator` | Governed inter-agent pipeline (advisory-only) |
| `build_action_plan` | Multi-step plans with dependency graph |
| `RecommendationValidator` | Contradictions, stale context, unsupported claims |
| `StrategicMemoryStore` | Deduped tenant analytical memory |
| `AIOperationalIntelligence` | Runtime health, degraded intelligence mode |
| `AIIntelligenceEngine` | Phase B entrypoint — analytics + decision + persist |

### Intelligence APIs (JWT + RLS)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ai/intelligence/runs` | Full intelligence pipeline → recommendation |
| `GET` | `/api/v1/ai/recommendations` | Paginated recommendations |
| `GET` | `/api/v1/ai/recommendations/{id}` | Recommendation detail |
| `GET` | `/api/v1/ai/recommendations/{id}/explainability` | Evidence + reasoning trace |
| `GET` | `/api/v1/ai/operational/status` | AI health and quality assessment |
| `POST` | `/api/v1/ai/recommendations/{id}/feedback` | Operator feedback / override notes |

### Operational lifecycle

1. Analytics run via `AIAnalyticsEngine` (Phase 2 path unchanged).
2. Multi-agent coordination scores and validates recommendation.
3. Governance gate assigns risk, trust, and approval requirement.
4. Persist to `ai_recommendations` (`PENDING_APPROVAL` when gated).
5. Strategic memory deduped write to `ai_strategic_memory`.
6. Operator reviews explainability; feedback to `ai_recommendation_feedback`.

### Migration

`0017_ai_intelligence_layer` — `ai_recommendations`, `ai_strategic_memory`, `ai_recommendation_feedback` with RLS.

## 2l. Enterprise autonomous operations (Phase C)

Phase C evolves the runtime control plane into a **semi-autonomous enterprise operations system** — policy-governed, auditable, reversible. Code: `app/runtime/enterprise/`.

| Document | Purpose |
|----------|---------|
| [docs/runtime/autonomous_operations.md](docs/runtime/autonomous_operations.md) | AutonomousOperationsEngine cycle |
| [docs/runtime/runtime_strategy.md](docs/runtime/runtime_strategy.md) | Adaptive orchestration advice |
| [docs/runtime/autonomous_governance.md](docs/runtime/autonomous_governance.md) | Safety levels, approval gates |
| [docs/runtime/scheduling_model.md](docs/runtime/scheduling_model.md) | Schedules, blackout, tenant policies |
| [docs/runtime/self_healing.md](docs/runtime/self_healing.md) | Recovery workflows |
| [docs/runtime/operational_forecasting.md](docs/runtime/operational_forecasting.md) | Predictive operational scores |

### Architecture (Phase C)

```mermaid
flowchart TB
  OW[orchestration_worker] --> CP[RuntimeControlPlane]
  CP --> SE[ScheduleExecutor]
  SE --> AOE[AutonomousOperationsEngine]
  AOE --> FC[RuntimeIntelligenceEngine]
  AOE --> DE[OperationalDecisionEngine]
  AOE --> GRE[GovernedRemediationExecutor]
  GRE --> AH[AutonomousHealer]
  AOE --> JOURNAL[(runtime_autonomous_actions)]
  SIM[OperationalSimulationEngine] --> AOE
```

| Component | Role |
|-----------|------|
| `AutonomousOperationsEngine` | Forecast → decide → plan → execute → journal |
| `AutonomyPermissionMatrix` | Safety levels, emergency stop, approval gates |
| `OperationalSimulationEngine` | Dry-run cycles without side effects |
| `RuntimeStrategyLayer` | Workload balancing and dispatch advice |
| `EnterpriseScheduleRegistry` | Blackout and maintenance windows |

### Enterprise ops APIs (JWT + RLS)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/ops/runtime/autonomy/status` | Safety level, kill switches, pending journal |
| `GET` | `/api/v1/ops/runtime/forecast` | Operational forecast scores |
| `POST` | `/api/v1/ops/runtime/simulation` | Dry-run operational cycle |
| `GET` | `/api/v1/ops/runtime/schedules` | Tenant schedule policy + blackout state |
| `GET` | `/api/v1/ops/runtime/remediation/history` | Autonomous action journal |

### Enterprise operational lifecycle

1. Orchestrator runs `RuntimeControlPlane` cycle (schedules + dispatch).
2. `ENTERPRISE_OPERATIONS` schedule triggers `AutonomousOperationsEngine`.
3. Forecast and decisions evaluated under `AutonomyPermissionMatrix`.
4. Remediation executes via bounded `AutonomousHealer` (reversible).
5. All actions journaled in `runtime_autonomous_actions` with provenance.
6. Operators review via ops APIs; simulation available before enabling actions.

### Configuration (Phase C)

| Env | Default | Purpose |
|-----|---------|---------|
| `RUNTIME_ENTERPRISE_OPS_ENABLED` | `true` | Master enterprise ops switch |
| `RUNTIME_AUTONOMY_SAFETY_LEVEL` | `standard` | `off` / `monitor` / `limited` / `standard` |

### Migration

`0018_enterprise_autonomous_ops` — `runtime_autonomous_actions`, `runtime_schedule_policies`.

## 2g. AI analytics engine

Production-grade **advisory** AI analytics on the deterministic platform — not a chatbot layer. Code: `app/ai/`. Maturity report: [docs/ai/ai_architecture_report.md](docs/ai/ai_architecture_report.md).

| Document | Purpose |
|----------|---------|
| [docs/ai/ai_architecture.md](docs/ai/ai_architecture.md) | Layer diagram, platform rules |
| [docs/ai/ai_lifecycle.md](docs/ai/ai_lifecycle.md) | Run states, API flow |
| [docs/ai/ai_governance.md](docs/ai/ai_governance.md) | May / must-never, approvals |
| [docs/ai/agent_model.md](docs/ai/agent_model.md) | Agents, tools, budgets |
| [docs/ai/prompt_contracts.md](docs/ai/prompt_contracts.md) | Versioned prompts |
| [docs/ai/ai_safety.md](docs/ai/ai_safety.md) | Tracing, injection, kill switches |
| [docs/ai/ai_operations.md](docs/ai/ai_operations.md) | Metrics, provider failures |
| [docs/ai/evaluation_framework.md](docs/ai/evaluation_framework.md) | Regression + eval cases |
| [docs/ai/decision_engine.md](docs/ai/decision_engine.md) | Phase B decision scoring |
| [docs/ai/multi_agent_architecture.md](docs/ai/multi_agent_architecture.md) | Multi-agent coordination |
| [docs/ai/explainability.md](docs/ai/explainability.md) | Evidence and reasoning traces |
| [docs/ai/recommendation_governance.md](docs/ai/recommendation_governance.md) | Approval and trust model |
| [docs/ai/evaluation_strategy.md](docs/ai/evaluation_strategy.md) | Intelligence eval suite |
| [docs/ai/strategic_memory.md](docs/ai/strategic_memory.md) | Tenant strategic memory |

### Architecture (Phase 2)

```mermaid
flowchart TB
  API["POST /api/v1/ai/runs"] --> ENG[AIAnalyticsEngine]
  ENG --> ORCH[AIOrchestrationService]
  ENG --> GND[GroundedContextDTO]
  ENG --> VAL[validate_insight_output]
  ENG --> LLM[LLMAdapter via factory]
  ORCH --> AUDIT[(ai_execution_runs)]
  ENG --> INS[(ai_insights advisory)]
  ENG --> MEM[(ai_session_turns)]
  LLM -.-x LED[Ledgers / snapshots]
```

| Component | Role |
|-----------|------|
| `AIAnalyticsEngine` | Workflows, provider call, validation, insight persist |
| `app/ai/providers/` | `LLMAdapter`, embedding/rerank/eval (mock + OpenAI-compatible) |
| `build_grounded_context` | Evidence refs, semantics version, freshness |
| `AISessionMemory` | Bounded tenant turns (non-authoritative) |
| `AIOrchestrationService` | Audit lifecycle, tool budgets |
| `AIService` + `app/api/ai.py` | JWT + RLS HTTP surface |

### Analytics workflows

| Workflow | Agent | Prompt |
|----------|-------|--------|
| `revenue_insight` | `analytics` | `analytics.summary.v1` |
| `anomaly_explanation` | `anomaly_investigation` | `anomaly.investigation.v1` |
| `inventory_insight` | `inventory_optimizer` | `inventory.insight.v1` |
| `forecast_prep` | `forecasting_assistant` | `forecast.prep.v1` |
| (+ trend, causal, recommendation, risk) | mapped in `app/ai/analytics/workflows.py` |

### AI APIs (JWT + RLS)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/ai/runs` | Execute workflow; returns run + validated insight |
| `GET` | `/api/v1/ai/runs` | Paginated execution audit |
| `GET` | `/api/v1/ai/runs/{id}` | Run detail |
| `GET` | `/api/v1/ai/executions/{id}` | Alias for run detail |
| `GET` | `/api/v1/ai/insights` | Paginated advisory insights |
| `GET` | `/api/v1/ai/insights/{id}` | Insight detail |

### AI lifecycle (summary)

1. Rate limit + `AI_ENABLED` + per-agent kill switch (`AI_DISABLED_AGENTS`).
2. Context assembly + grounding (semantics, rebuild state, evidence).
3. Provider completion (default `AI_PROVIDER=mock` for CI).
4. Validation (confidence, stale-data, unsupported claims).
5. Optional advisory persist to `ai_insights` (never ledger).
6. Audit finalize on `ai_execution_runs`.

### Governance & safety (unchanged invariants)

- **Advisory only** — AI never mutates append-only ledgers or snapshots.
- **Forbidden:** rebuild trigger, queue claim, RLS/semantics bypass.
- **Outputs include:** `confidence`, `degraded_mode`, `stale_data_warning`, `semantics_version`.
- **Observability:** `ai_run_*`, `ai_insight_generated`, `ai_tool_call`, token/latency fields on run rows.

### Configuration (see §19)

`AI_PROVIDER`, `AI_OPENAI_*`, `AI_RATE_LIMIT_PER_MINUTE`, `AI_MEMORY_MAX_TURNS`, `AI_DISABLED_AGENTS`.

### Extension model

1. Add `PromptContract` + workflow mapping.
2. Add eval case in `tests/unit/test_ai_prompt_regression.py`.
3. Register agent permissions in `app/ai/agents.py`.
4. Optional: new adapter in `app/ai/providers/` + factory branch.

Migrations: `0013_ai_execution_runs`, `0014_ai_analytics_engine` (session memory + insight metadata).

## 2h. Platform stabilization (Phase 1)

Entropy reduction without redesigning core architecture. Full report: [docs/architecture/stabilization_report.md](docs/architecture/stabilization_report.md).

### Stabilization status

| Check | Target |
|-------|--------|
| Unit tests | `pytest tests/unit -q` |
| Integration | `pytest tests/integration -m integration` (Postgres + `alembic upgrade head`) |
| Lint | `ruff check .` |
| Types | `mypy app tests` |
| Governance | `python scripts/architecture_governance_check.py` |

### Architecture boundaries (post-cleanup)

| Layer | Responsibility | Notes |
|-------|----------------|-------|
| `app/api` | HTTP, auth, DTO mapping | No direct `app.etl.*` imports; uploads via `report_upload_service` |
| `app/services` | Use-case orchestration | May call ETL loaders only through facades (e.g. upload service) |
| `app/etl` | Ingest, persist, worker | `pipeline.py` orchestrates; `persist_*.py` / `pipeline_analytics.py` are internal |
| `app/domain` | Pure rules | No SQLAlchemy; one allowlisted `analytics_payload` bridge |
| `app/runtime` | Rebuild dispatch | Must not import `app.api` |

### Cleanup results

- **WB persist** split into `persist_layers.py` + `persist_aggregates.py` (public `WbFinancialPersistService` unchanged).
- **ETL pipeline** slimmed; legacy analytics in `pipeline_analytics.py`; operator CLI: `python -m app.etl.pipeline_standalone <report_id>`.
- **108** ruff auto-fixes; import sort normalized repo-wide.
- **Mypy** clean on `app` + `tests` (25 issues resolved).
- **Governance** hardened: services/runtime import rules, API `db.commit` ban, stabilization doc required.

### Remaining debt (tracked)

- Grandfathered LOC: `inventory_consistency_verification.py`, `operations/recovery.py`.
- Move `AnalyticsPayload` from `app/etl/types` to `app/dto` (drop domain allowlist).
- E501 in non-parser `app/` modules — fix incrementally.
- StrEnum `UP042` bulk migration deferred.

### Developer workflow

1. Run governance check before PRs touching governed paths.
2. New upload/validation logic → `app/services/report_upload_service.py`, not `app/api/reports.py`.
3. Manual pipeline debug → `pipeline_standalone`, not inline `__main__` in `pipeline.py`.
4. Integration DB cleanup skips missing tables (safe on partial migrations).

### ADR index (decisions)

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/architecture/adr/ADR-001-append-only-ledger.md) | Append-only ledgers |
| [ADR-002](docs/architecture/adr/ADR-002-advisory-locking.md) | `pg_try_advisory_xact_lock` per tenant |
| [ADR-003](docs/architecture/adr/ADR-003-staging-promote.md) | Staging + atomic promote |
| [ADR-004](docs/architecture/adr/ADR-004-deterministic-rebuild.md) | Deterministic rebuild + fingerprints |
| [ADR-005](docs/architecture/adr/ADR-005-streaming-replay.md) | Grouped streaming replay |
| [ADR-006](docs/architecture/adr/ADR-006-queue-skip-locked.md) | `SKIP LOCKED` job queue |
| [ADR-007](docs/architecture/adr/ADR-007-semantics-governance.md) | Semantics lifecycle, no silent fallback |
| [ADR-008](docs/architecture/adr/ADR-008-anomaly-quarantine.md) | Isolated best-effort anomaly persist |

### Engineering standards (summary)

- Orchestration modules target **≤200 LOC**; grandfathered large files reduced when touched.
- Domain stays pure; ETL orchestrates; API does not compute money.
- Migrations documented in README §18; RLS matches session model.
- Integration tests: isolated DB, deterministic fixtures, replay equivalence tests.

### AI-safe modification policy (summary)

**Safe:** additive APIs, tests, docs, log-only probes, bug fixes preserving invariants.

**Requires integration rerun:** queue, rebuild, persist txn, RLS, semantics.

**Requires benchmark:** streaming/rebuild hot paths (`RUN_STRESS_TESTS`).

**Forbidden:** removing advisory try-locks, blocking locks, ledger mutation, inline semantics rebuild, shared txn for anomalies, `SKIP LOCKED` removal, silent semantics fallback.

Full rules: [ai_change_policy.md](docs/architecture/ai_change_policy.md).

### Automated light checks

```bash
python scripts/architecture_governance_check.py
```

Checks: forbidden patterns (blocking advisory lock, RLS bypass misuse), LOC warnings, git-diff hints for ADR/README when governed paths change, migration README mentions.

**Why governance reduces entropy:** ADRs capture *why* unsafe shortcuts were rejected. AI tools optimize locally (fewer lines, one transaction, “helpful” fallbacks) — without ADRs + invariants + CI hints, each PR re-litigates the same failures. Governance makes the default path the safe path.

## 2d. Operational architecture

Read-only operational layer around existing ETL/rebuild/queue (no business mutations via ops API).

| Document | Purpose |
|----------|---------|
| [docs/operations/operational_model.md](docs/operations/operational_model.md) | Lifecycle models (rebuild, queue, anomaly, drift, DLQ) |
| [docs/operations/metrics_catalog.md](docs/operations/metrics_catalog.md) | Structured log metrics |
| [docs/operations/alerting_model.md](docs/operations/alerting_model.md) | Critical/warning alerts and SLA guidance |
| [docs/operations/disaster_recovery.md](docs/operations/disaster_recovery.md) | Recovery playbooks |
| [docs/operations/failure_modes.md](docs/operations/failure_modes.md) | Failure mode analysis (detection / containment / recovery) |
| [docs/operations/performance_budget.md](docs/operations/performance_budget.md) | Rebuild, WAL, queue, contention budgets |
| [docs/operations/release_checklist.md](docs/operations/release_checklist.md) | Pre-release validation checklist |

### Operational endpoints (JWT, tenant-scoped)

Prefix: `/api/v1/ops` — all **GET**, paginated (`skip`, `limit`).

| Endpoint | Data |
|----------|------|
| `/ops/rebuilds` | `snapshot_rebuild_requirements` + orchestration metadata |
| `/ops/anomalies` | `etl_anomalies` |
| `/ops/drift-checks` | `snapshot_consistency_checks` |
| `/ops/queue` | `etl_jobs` + `status_counts` |
| `/ops/dead-letters` | `etl_jobs` where `status=dead_letter` |
| `/ops/semantics-status` | `semantics_lifecycle_versions` (global registry) |

### Rebuild orchestration foundation

Migration `0012` adds orchestration columns (status, priority, retry metadata) to `snapshot_rebuild_requirements`.

- **Priorities:** `RebuildPriority` (lower = sooner)
- **Status machine:** `RebuildOrchestrationService` (`pending` → `running` → `succeeded` / `deferred` / `failed`)
- **Fairness / throttle:** `select_fair_batch`, `TenantThrottlePolicy` (1 concurrent rebuild/tenant — matches advisory lock)

**Runtime dispatch:** separate orchestrator process (`python -m app.runtime.orchestration_worker`) consumes `snapshot_rebuild_requirements` via `RebuildDispatcher`. ETL persist still runs incremental rebuild on ingest (advisory lock serializes with orchestrator).

### Observability model

- JSON logs + `record_metrics` / `track_rebuild` (no Prometheus required in-repo).
- Ops API for tenant dashboards/automation precursors.
- Alerting: log event names in [alerting_model.md](docs/operations/alerting_model.md).

### Failure recovery (explicit primitives)

`TenantRecoveryService` (`app/operations/recovery.py`) — **no hidden retries**; invoke from worker maintenance hooks or operator runbooks:

| Method | Use when |
|--------|----------|
| `reset_stale_running_rebuilds` | Orchestration stuck `running` after crash |
| `cleanup_orphaned_staging` | Staging rows left after failed full promote |
| `recover_stuck_processing_jobs` | Tenant-scoped visibility recovery |
| `replay_dead_letter_job` | Operator-approved DLQ replay (`reset_attempt_counter` optional) |
| `apply_rebuild_retry_backoff` | Deferred rebuild rows missing `next_eligible_at` |

Playbooks: [failure_modes.md](docs/operations/failure_modes.md), [disaster_recovery.md](docs/operations/disaster_recovery.md).

### Operational safeguards (structured logs)

`ProductionSafetyGuards` + `warn_rebuild_duration_high` / `warn_wal_growth_high` — thresholds via env (`OPS_REBUILD_DURATION_WARN_MS`, `OPS_QUEUE_LAG_WARN_SECONDS`, etc.). Events: `ops_rebuild_duration_high`, `ops_wal_growth_high`, `ops_queue_lag_high`, `ops_anomaly_explosion`, `ops_drift_frequency_high`. See [metrics_catalog.md](docs/operations/metrics_catalog.md).

### Performance budgets & release governance

- Budgets: [performance_budget.md](docs/operations/performance_budget.md) (rebuild duration, memory, WAL, queue lag, contention).
- Pre-release: [release_checklist.md](docs/operations/release_checklist.md) (migrations, replay equivalence, benchmarks, drift, queue lifecycle, README).

**Why ops visibility before AI analytics expansion:** Analytics features assume trustworthy inventory and job completion. Without lifecycle visibility, drift and DLQ failures surface as “bad AI insights” instead of operational incidents.

**Why deterministic recovery:** Marketplace analytics must be replayable from the append-only ledger. Explicit, idempotent recovery steps preserve tenant isolation and make incident response auditable — unlike opaque retry storms that can double-apply semantics or promote partial staging.

## 3. Wildberries Financial Pipeline

WB uploads never overwrite prior reports. Each upload creates a new immutable snapshot and derived layers.

```mermaid
flowchart LR
  A[RAW FILE in storage] --> B[Parser strategy]
  B --> C[Normalization]
  C --> D[Financial ledger]
  D --> E[Aggregates]
  E --> F[Analytics DTO / AI context]
```

| Stage | Layer | Output |
|-------|--------|--------|
| 1 | Storage + `raw_reports` | Checksum, URI, parser version metadata |
| 2 | `app/parsers/wb/` | `NormalizedWbRow` list (tolerant column matching) |
| 3 | `normalized_report_rows` | Canonical JSONB per source row |
| 4 | `app/domain/finance/` | `financial_ledger_entries` (one row per operation) |
| 4b | `app/domain/inventory/` | `inventory_ledger_entries` (SKU quantity movements, parallel to finance) |
| 5 | `app/domain/reconciliation/` | `report_reconciliations` (expected vs actual payout) |
| 6 | `app/domain/analytics/` | `daily_aggregates`, `sku_daily_metrics` |
| 7 | `app/dto/` | `AnalyticsPayload` for API + AI insights |

Orchestration lives in `app/etl/wb/processor.py` (CPU) and `app/etl/wb/persist.py` (DB). The generic `ETLPipeline` routes `Marketplace.WILDBERRIES` to this path without changing report API contracts.

## 4. Historical Storage Model

| Table | Purpose |
|-------|---------|
| `raw_reports` | Immutable file reference + parser metadata (never overwritten) |
| `normalized_report_rows` | Row-level canonical fields + raw cell snapshot |
| `financial_ledger_entries` | Atomic financial operations |
| `inventory_ledger_entries` | Append-only SKU inventory movements (separate from finance) |
| `warehouse_stock_snapshots` | Rebuildable daily stock state and discrepancy valuation |
| `daily_aggregates` | Materialized day-level KPIs |
| `sku_daily_metrics` | Materialized SKU-day profitability |
| `report_reconciliations` | Payout reconciliation snapshot per report |
| `cost_history` | Time-effective unit economics (historical COGS) |

Properties:

- **Append-only reports** — new upload = new `report_id`, full history retained
- **Period analysis** — query aggregates/ledger by date range across reports
- **Retrospective recalc** — re-run worker on same checksum is idempotent (no duplicate ledger)
- **Period comparison** — compare `daily_aggregates` / `sku_daily_metrics` across `report_id` or date windows

Raw bytes stay in object storage; normalized and ledger data stay in PostgreSQL.

## 5. Parser Strategy Architecture (WB)

Location: `app/parsers/wb/`

```
app/parsers/wb/
  base.py          # column resolution, Decimal/date parsing
  mapping.py       # canonical fields + alias registry
  strategies/
    realization_v1.py
    realization_v2.py
```

Design rules:

- **No hardcoded** `df["Цена"]` — use `resolve_column_map()` + `FIELD_ALIASES`
- **Tolerant matching** — normalized headers, substring alias match
- **Versioned strategies** — `supports(df)` picks v1/v2; stored on `raw_reports.parser_version`
- **Canonical mapping** — all strategies emit the same `CANONICAL_FIELDS`

When WB changes column names or order, add aliases in `mapping.py` or a new strategy — existing reports remain valid.

**Inventory operation semantics:** `app/parsers/wb/operation_semantics.py` maps unstable WB operation labels (RU/EN, substring-tolerant) to `InventoryOperationType`. Registries: `SALE_OPERATIONS`, `RETURN_OPERATIONS`, `LOSS_OPERATIONS`, `DEFECT_OPERATIONS`, `COMPENSATION_OPERATIONS`, `INBOUND_OPERATIONS`, `TRANSFER_OPERATIONS`, plus write-off and inventory-adjustment aliases.

## 6. Financial Ledger

Every monetary movement is stored as its own row in `financial_ledger_entries`.

Operation types (`LedgerOperationType`):

`sale`, `return`, `logistics`, `storage_fee`, `commission`, `penalty`, `acquiring`, `compensation`, `payout`, `deduction`, `advertisement`, `other`

Each entry:

- `report_id`, `operation_date`, `sku`, `nm_id`, `operation_type`
- `amount` — **Numeric/Decimal only** (no `float` in domain or persist)
- `currency`, `source_row_id` (idempotency key), `metadata` JSONB

Building logic: `app/domain/finance/ledger.py` (`LedgerBuilder`).

## 6b. Inventory Ledger (foundation)

Independent from `financial_ledger_entries`.

| Field | Role |
|-------|------|
| `operation_date`, `sku`, `nm_id`, `warehouse_name` | Movement dimensions |
| `operation_type` | `InventoryOperationType` (see below) |
| `quantity_delta` | Signed integer; immutable after insert |
| `cost_per_unit`, `total_cost_delta` | Historical COGS from `cost_history` on `operation_date` |
| `sale_price_per_unit`, `total_sale_delta` | Retail-side amounts (`Decimal` only) |
| `source_row_id` | Idempotency key (with `report_id` + `operation_type`) |
| `semantics_version` | Frozen WB operation semantics version (e.g. `1.0`) |
| `canonical_payload`, `raw_payload` | Preserved WB row context |

Operation types (`InventoryOperationType`):

`inbound`, `sale`, `return`, `logistics_loss`, `warehouse_loss`, `defect`, `writeoff`, `transfer`, `compensation`, `inventory_adjustment`

WB operation labels are mapped via `app/parsers/wb/operation_semantics.py` (aliases + fuzzy normalization). Movement extraction: `app/domain/inventory/movements.py` (`InventoryMovementBuilder`). Persist: `WbFinancialPersistService._persist_inventory_ledger()` with `ON CONFLICT DO NOTHING` on `(report_id, source_row_id, operation_type)`.

The inventory ledger is **append-only** — snapshots and aggregates may be rebuilt; ledger rows are never updated or deleted.

## 6c. Stock reconstruction and loss analytics

Table: `warehouse_stock_snapshots` — daily deterministic stock state per `(user_id, snapshot_date, sku, warehouse_name)`.

| Field | Role |
|-------|------|
| `opening_stock` … `writeoff_units` | Signed integer rollups from ledger for the day |
| `expected_closing_stock` | `opening + inbound - sold + returned - lost - writeoffs` |
| `actual_stock` | `expected_closing + inventory_adjustment deltas` |
| `discrepancy_units` | `actual_stock - expected_closing_stock` |
| `discrepancy_cost`, `discrepancy_sale_value` | `Decimal` valuation on `snapshot_date` |

Services (pure domain, no heuristics):

| Service | Module | Role |
|---------|--------|------|
| `InventoryReconstructionService` | `app/domain/inventory/reconstruction.py` | Rebuild snapshots from immutable `inventory_ledger_entries` |
| `InventoryReconciliationService` | `app/domain/inventory/reconciliation.py` | Discrepancy + loss valuation via `cost_history` effective on `snapshot_date` |
| `InventorySnapshotPipeline` | `app/domain/inventory/pipeline.py` | Orchestrates rebuild → reconcile → loss analytics |

**Semantics versioning:** `SEMANTICS_VERSION` in `app/parsers/wb/semantics.py` is stored on `normalized_report_rows` and `inventory_ledger_entries`. `InventoryReconstructionService` selects `SEMANTICS_REGISTRY[row.semantics_version]` so historical rows keep v1.0 classification after future parser upgrades.

**Snapshot lifecycle** (`InventorySnapshotRebuildService` in `app/etl/wb/inventory_snapshot_rebuild.py`):

Snapshots are **derived state** rebuilt from the append-only `inventory_ledger_entries` ledger. They may be deleted and recomputed at any time inside a tenant rebuild window without mutating ledger rows.

**Full rebuild staging promote** (`FullInventoryRebuildService` + `warehouse_stock_snapshots_staging`):

1. Stream ledger → compute snapshots in memory.
2. Bulk insert into `warehouse_stock_snapshots_staging` (tagged with `rebuild_run_id`).
3. Inside the **same transaction**: `DELETE` all live `warehouse_stock_snapshots` for the tenant → `INSERT … SELECT` from staging into live (atomic promote).
4. Clear staging rows for the run → commit.

Readers outside the transaction never observe an empty live table or a mix of deleted and half-inserted rows: they see either the **previous committed** snapshot set or the **new committed** set (PostgreSQL MVCC).

**Advisory locking model:**

- `pg_try_advisory_xact_lock(namespace, key)` per `user_id` (namespace `83472933`, key derived from `user_id`).
- **Non-blocking:** contended rebuild raises `InventoryRebuildBusyError` immediately (retryable; no `pg_advisory_lock` wait).
- Lock is **transaction-scoped** (`xact_lock`): released on commit/rollback — no orphaned locks after crashes.
- ETL persist and rebuild share the same lock domain per tenant so snapshot recompute serializes safely.

**Visibility guarantees (production):**

| Observer | During uncommitted rebuild txn | After commit |
|----------|-------------------------------|--------------|
| Other sessions (READ COMMITTED) | Previous complete live snapshots | New complete live snapshots |
| Live table | Never reads staging | Never partial promote |
| `inventory_ledger_entries` | Unchanged (append-only) | Unchanged |

**Concurrency behavior:**

- Parallel **incremental** rebuilds for one tenant: at most one holds the lock; others fail fast.
- Parallel **persist + rebuild**: persist may complete; overlapping rebuild attempts serialize via the same advisory lock.
- **Drift verification** (`InventoryConsistencyVerificationService`): replays ledger in memory, records `snapshot_consistency_checks` and `inventory_integrity_anomalies` on mismatch — does **not** mutate live snapshots or ledger.

**Rebuild determinism (incremental):**

1. Compute window: `rebuild_from = earliest_affected_date`, `rebuild_to = max(latest_snapshot_date, latest_ledger_date)` so corrections on date T invalidate all dependent future balances.
2. In one transaction: try-lock → `DELETE` snapshots where `rebuild_from <= snapshot_date <= rebuild_to` → recompute → bulk upsert → commit (no partial visibility).
3. **Incremental rebuild:** carry-forward `actual_stock` from the latest snapshot strictly before `rebuild_from` per `(sku, nm_id, warehouse_name)` when present; otherwise scan ledger history before `rebuild_from`. Only days inside the window are emitted.
4. Semantics: each ledger row is classified with `SEMANTICS_REGISTRY[row.semantics_version]` (no fallback to current parser defaults).

**Integration proof suite:** `tests/integration/test_rebuild_production_guarantees.py` (visibility, advisory lock timing, persist/rebuild contention, drift E2E).

### Streaming guarantees

`InventoryLedgerStreamingService` replays `inventory_ledger_entries` with a **server-side cursor** (`stream_results=True`), ordered deterministically:

`sku → warehouse → operation_date → created_at → source_row_id`

| Property | Guarantee |
|----------|-----------|
| **Grouping** | Yields one `(sku, nm_id, warehouse)` group at a time; prior group is released before the next |
| **Ordering** | Stable across replays; matches domain `InventorySnapshotPipeline` expectations |
| **Memory (ledger path)** | Peak client RAM scales with **max rows per group**, not total ledger size (see benchmark) |
| **Incremental filter** | Rows before `rebuild_from` skipped only for keys in `carry_forward_keys` |

Snapshot **drafts** for the full rebuild are accumulated before staging bulk insert — memory also scales with emitted snapshot row count (typically « ledger rows for dense daily SKU/warehouse grids).

### Rebuild scalability and performance

| Mode | Work done | Typical use |
|------|-----------|-------------|
| **Incremental** | Delete window `[rebuild_from … rebuild_to]` → stream replay → upsert live | ETL persist after each report |
| **Full** | Staging bulk load → atomic promote (delete all live → insert from staging) | Drift repair, semantics migration, empty snapshots |

**Benchmark suite** (synthetic tenant, gated by `RUN_STRESS_TESTS=true`):

`tests/integration/test_inventory_rebuild_benchmark.py` + `tests/integration/inventory_scale_fixtures.py`

Dataset: **52 000** append-only ledger rows, **200** SKUs × **5** warehouses, **52** movements per SKU/warehouse (realistic multi-key grid).

**Reference run** (local PostgreSQL 16, `localhost:5434`, Windows dev host, May 2026 — **not a SLA**):

| Metric | Observed |
|--------|----------|
| Stream groups | 1 000 |
| Max rows per group | 52 |
| Stream replay peak RAM | ~175 MiB |
| Full rebuild duration | ~13.5 s (~3 850 ledger rows/s) |
| Snapshot rows emitted | 52 000 |
| Incremental full-window rebuild | ~15.5 s |
| Advisory lock + full rebuild txn | ~16.6 s |
| WAL bytes delta (`pg_stat_wal` cumulative) | ~155 MB over seed + 2× full rebuild |
| Deterministic replay (2× full) | Fingerprints identical |
| Full vs incremental equivalence | Fingerprint maps match |

```bash
set RUN_INTEGRATION_TESTS=true
set RUN_STRESS_TESTS=true
set TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test
pytest tests/integration/test_inventory_rebuild_benchmark.py -v -s
# Optional override: SCALE_LEDGER_ROWS=60000 (minimum 50000 enforced)
```

Unit-level equivalence (in-memory ledger, no DB): `tests/unit/test_full_incremental_rebuild_equivalence.py`.

### Operational recommendations

1. **Prefer incremental rebuild** after routine ETL — smaller delete window, reuses carry-forward openings when prior snapshots exist.
2. **Schedule full rebuild** off-peak for large tenants; holds advisory lock for the whole promote transaction; monitor `advisory_lock_contention` metric.
3. **Watch snapshot row cardinality** — dense `(sku, warehouse, day)` grids grow snapshot storage and rebuild RAM linearly; archive old reports at the business layer if history is huge.
4. **Do not load entire ledger into application memory** outside the streaming service — benchmarks confirm grouped cursor replay stays bounded per group.
5. **WAL / I/O** — full promote is delete-all + bulk insert per tenant; on managed Postgres, run benchmarks after major releases; compare `pg_stat_wal` delta and `track_rebuild` logs.
6. **Concurrency** — one rebuild per tenant at a time; parallel workers on different tenants scale linearly until CPU/IO saturated.

**Decimal guarantees:** Unit counts are integers; money fields (`discrepancy_cost`, `discrepancy_sale_value`, loss analytics, sale averages) use `Decimal` end-to-end in reconstruction, reconciliation, and valuation — no `float`, no silent coercion.

**Opening balance integrity:** movements with `canonical_payload.is_opening_balance` require a SKU and an `opening_effective_date` (ISO date in payload, or `operation_date` as fallback) **strictly before** the earliest ledger operation for the same SKU/warehouse (persisted history and the current import batch). No auto-shifting or silent correction — violations raise `OpeningBalanceIntegrityError`.

**AI analytics extension** (additive keys on `analytics_payload` / `ai_insights.context_payload`):

`inventory_losses_units`, `inventory_losses_cost`, `inventory_losses_sale_value`, `warehouse_discrepancies`, `top_loss_skus` — merged via `app/domain/inventory/analytics_payload.py` after persist rebuild.

## 7. Payout Reconciliation (MVP)

`app/domain/reconciliation/calculator.py` computes:

| Metric | Meaning |
|--------|---------|
| `gross_revenue` | Retail / sale-side inflow |
| `net_revenue` | After returns and sale adjustments |
| `wb_commissions` | Marketplace commission total |
| `logistics` | Delivery / logistics charges |
| `deductions` | Other withholdings |
| `returns` | Return impact |
| `expected_payout` | Modelled transfer from WB |
| `actual_payout` | Payout lines from report |
| `difference` | `actual_payout - expected_payout` |

Persisted per report in `report_reconciliations`. Same inputs always yield the same `Decimal` result.

## 8. Historical Cost System

Table: `cost_history`

| Field | Role |
|-------|------|
| `internal_sku` | SKU key |
| `effective_from` | Cost valid from this date (inclusive) |
| `product_cost`, `packaging_cost`, `inbound_logistics_cost`, `additional_cost` | Unit cost components |
| `cost` | Total unit cost (denormalized sum) |
| `currency`, `comment`, `created_at` | Audit trail |

Profitability uses **cost effective on sale date**, not latest cost (`WbFinancialProcessor.enrich_with_costs`).

API (additive, does not change report contracts):

- `POST /api/v1/costs` — manual create
- `POST /api/v1/costs/import` — bulk Excel/CSV (tolerant column aliases)
- `GET /api/v1/costs` — list (optional `?sku=`)
- `GET /api/v1/costs/{id}` — single record

## 9. Aggregation Layer

Materialized tables — **do not** re-scan all normalized rows on every API read.

| Table | Granularity | Examples |
|-------|-------------|----------|
| `daily_aggregates` | tenant + day | revenue, net profit, margin, ROI |
| `sku_daily_metrics` | tenant + SKU + day | units sold, return rate, buyout rate, average check |

Logic: `app/domain/analytics/aggregation.py`. Rebuilt idempotently on persist (upsert by natural keys).

## 10. Domain Layer (Money Rules)

All business math lives under:

- `app/domain/finance/` — ledger drafts, cost snapshots
- `app/domain/inventory/` — movements, reconstruction, reconciliation, loss analytics
- `app/domain/reconciliation/` — payout reconciliation
- `app/domain/analytics/` — aggregates and profitability

**Forbidden:** calculating money in `app/api/*` or worker orchestration code. API and worker only orchestrate; domain computes.

## 11. Idempotency

| Mechanism | Behavior |
|-----------|----------|
| Upload `file_checksum` | Duplicate file → existing report / job handling |
| `financial_ledger_entries.source_row_id` | `ON CONFLICT DO NOTHING` — no duplicate ledger on re-run |
| `inventory_ledger_entries` | `ON CONFLICT DO NOTHING` on `(report_id, source_row_id, operation_type)` |
| `warehouse_stock_snapshots` | Upsert on `(user_id, snapshot_date, sku, warehouse_name)` — safe to rebuild |
| Aggregates | Upsert on `(user_id, metric_date, …)` keys |
| AI insights | Idempotent insert by `report_id` in payload |

Re-uploading the same report checksum is safe and deterministic.

## 12. Async + RLS Model

```sql
user_id = current_setting('app.current_user_id')::uuid
OR current_setting('app.queue_role', true)::boolean = true
OR current_setting('app.bypass_rls', true)::boolean = true
```

| Context | Purpose |
|---------|---------|
| `TenantSession` | API + worker business writes |
| `QueueSession` | Queue broker (`etl_jobs` only) |
| `SystemSession` | Alembic / maintenance only |

No global RLS bypass in runtime paths.

## 13. Queue Architecture

Processing lifecycle source of truth: **`etl_jobs.status`**.

`reports.status` is legacy; API status is projected from the latest job via `app/schemas/report_projection.py`.

`QueueBackend` (`app/core/queue/backend.py`):

`enqueue`, `claim`, `ack`, `fail`, `requeue`, `recover_stale`, `heartbeat`

Implementation: `PostgresQueueBackend` (`SELECT … FOR UPDATE SKIP LOCKED` on `etl_jobs`).

### Queue guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| **No duplicate active work** | `claim()` only selects `PENDING` rows; claimed row becomes `PROCESSING` before commit |
| **No orphan `PROCESSING` after success** | `ack()` clears `claimed_at` and sets `COMPLETED` in the same tenant transaction as persist |
| **At-least-once attempts** | `attempt_count` increments on every `claim()`; failures return to `PENDING` until `max_attempts` |
| **Idempotent enqueue** | Same `(user_id, idempotency_key)` returns the existing row while status is `PENDING` or `PROCESSING` |
| **Broker isolation** | `QueueSession` (`app.queue_role`) for `claim` / `recover_stale`; tenant data via `TenantSession` |

### Retry semantics

- On `fail(job_id, attempt_count=…, max_attempts=…)`:
  - `attempt_count < max_attempts` → `PENDING` (retryable; `claimed_at` / `processing_started_at` cleared)
  - `attempt_count >= max_attempts` or `poison=True` → `DEAD_LETTER`
- `requeue()` only from `FAILED` / `DEAD_LETTER` when `attempt_count < max_attempts` (manual operator path).
- Worker passes the **post-claim** `attempt_count` from `ClaimedJobRecord` into `fail()` — retries are deterministic and bounded.

### Visibility timeout behavior

While `PROCESSING`, a job is considered stale when **either**:

- `now > claimed_at + visibility_timeout_seconds`, or
- `now > last_heartbeat_at + visibility_timeout_seconds`

`recover_stale()` (also run at the start of each worker iteration):

- Requeues to `PENDING` when `attempt_count < max_attempts` (`last_error`: visibility timeout expired)
- Moves to `DEAD_LETTER` when attempts are exhausted after timeout
- Uses `SKIP LOCKED` so multiple workers can recover different rows without blocking

`heartbeat()` refreshes `last_heartbeat_at` during long CPU-bound ETL (default worker interval: 15s).

**Integration proof suite:** `tests/integration/test_queue_lifecycle.py` and `tests/integration/test_queue_backend.py` (backdated timestamps — no wall-clock sleep for timeout tests).

## 14. Worker Lifecycle

1. **`recover_stale()`** — reclaim visibility-expired `PROCESSING` jobs before claiming new work
2. **`claim()`** under `QueueSession` — single row, `SKIP LOCKED`, increments `attempt_count`
3. **CPU ETL** (`process_content`) — no DB transaction held
4. **Heartbeat loop** — `heartbeat()` every 15s while job is current
5. **`TenantSession` transaction:**
   - WB: `WbFinancialPersistService.persist()` (raw → normalized → ledger → inventory ledger → warehouse snapshots → reconciliation → aggregates)
   - Legacy marketplaces: `raw_data` JSONB on report
   - Idempotent `ai_insights`
   - **`ack()`** job → `COMPLETED`
6. **On failure:** `fail()` → `PENDING` (retry) or `DEAD_LETTER` (poison / max attempts)
7. **Shutdown:** `SIGINT` / `SIGTERM` marks in-flight job via `fail()` if interrupted mid-processing

### Concurrency behavior

- Multiple worker processes may call `claim()` concurrently; PostgreSQL grants each worker a different row (`SKIP LOCKED`).
- A second `claim()` on the same job while it remains `PROCESSING` returns `None` for that job (not double-processed).
- Poll interval when idle: 2s (`run_worker`); recovery is not sleep-driven — it is evaluated on each loop iteration.

## 15. Clean Architecture Layers

| Layer | Responsibility |
|-------|----------------|
| `app/api` | HTTP transport |
| `app/schemas` | API contracts + projections |
| `app/services` | Tenant-scoped orchestration |
| `app/domain` | Pure finance/analytics/reconciliation |
| `app/parsers` | Marketplace file parsing strategies |
| `app/etl` | Worker, pipeline, WB persist |
| `app/dto` | Cross-layer immutable contracts |
| `app/core/queue` | Queue abstraction |
| `app/storage` | Object storage |
| `app/models` | SQLAlchemy persistence |

## 16. Docker Deployment

```bash
cp .env.example .env
docker compose up --build
```

Services: `postgres`, `migrate` (Alembic + advisory lock), `api`, `worker`, `orchestrator`, `nginx`

Health: `GET /health`, `GET /health/ready`

## 17. Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
python -m app.etl.worker
python -m app.runtime.orchestration_worker
```

### Local PostgreSQL for integration tests

Use a dedicated database (not production). Typical local setup:

| Setting | Example |
|---------|---------|
| Host port | `5434` (avoids conflict with other Postgres on `5432`) |
| Database | `marketplace_test` |
| URL | `postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test` |

```bash
# Create DB once (psql or docker)
createdb -h localhost -p 5434 -U postgres marketplace_test

set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test
set TEST_DATABASE_URL=%DATABASE_URL%
set SECRET_KEY=test-secret-key
alembic upgrade head
```

Docker Compose maps project Postgres to `5432`; if that port is taken, use an external test instance on another port or change the compose port mapping.

## 18. Alembic / Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic current
alembic history
alembic heads
alembic upgrade head
alembic downgrade -1
```

Run commands from the **repository root** (`.venv` activated). `alembic.ini` sets `prepend_sys_path = .` so migration helpers import as `migrations_support.pg_enum` — no manual `PYTHONPATH` required.

WB financial tables: migration `0005_wb_financial_platform.py`. Inventory ledger: `0006_inventory_ledger.py`. Warehouse snapshots: `0007_warehouse_stock_snapshots.py`. Inventory hardening (semantics version, composite indexes): `0008_inventory_hardening.py`. Rebuild orchestration: `0012_rebuild_orchestration_ops.py`. AI execution audit: `0013_ai_execution_runs.py`. AI analytics engine: `0014_ai_analytics_engine.py`. Runtime autonomy audit: `0015_runtime_autonomy_events.py`. Production reliability: `0016_production_reliability.py`.

Docker: `scripts/entrypoint-migrate.sh` uses `pg_advisory_lock` (`MIGRATION_LOCK_KEY`).

### Alembic troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: migrations_support` | Run Alembic from repo root; ensure `prepend_sys_path = .` in `alembic.ini`. |
| `ModuleNotFoundError: pg_enum` | Old revisions: use `migrations_support.pg_enum` (or `alembic/pg_enum.py` shim). |
| Migrations apply but tables missing | Async migrations must commit: `alembic/env.py` uses `connectable.begin()`, not bare `connect()`. |
| `relation "users" does not exist` in tests | `alembic upgrade head` against `TEST_DATABASE_URL` before `pytest tests/integration`. |
| Downgrade fails on ENUM types | Review revision `downgrade()`; some ENUM drops are intentionally conservative. |

## 19. Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL URL |
| `SECRET_KEY` | JWT signing key |
| `STORAGE_BACKEND` | `supabase` or `local` |
| `ALLOW_LOCAL_STORAGE_FALLBACK` | Local uploads in dev |
| `SUPABASE_URL` / `SUPABASE_KEY` | Remote storage |
| `JOB_MAX_ATTEMPTS` | Queue retry limit |
| `JOB_VISIBILITY_TIMEOUT_SECONDS` | Claim/heartbeat timeout |
| `LOG_LEVEL` | JSON log level |
| `MIGRATION_LOCK_KEY` | Advisory lock for migrations |
| `ORCHESTRATOR_*` | Rebuild dispatcher poll, batch, maintenance (see §2f) |
| `AI_ENABLED` | Master switch for AI runs |
| `AI_PROVIDER` | `mock` (default) or `openai_compatible` |
| `AI_OPENAI_BASE_URL` / `AI_OPENAI_API_KEY` / `AI_OPENAI_MODEL` | External LLM when provider is `openai_compatible` |
| `AI_PROVIDER_MAX_RETRIES` | Bounded provider retries |
| `AI_RATE_LIMIT_PER_MINUTE` | Per-tenant run rate limit (0 = off) |
| `AI_MEMORY_MAX_TURNS` | Max `ai_session_turns` per session |
| `AI_DISABLED_AGENTS` | Comma-separated `AgentKind` kill switch |
| `AI_EXECUTION_TIMEOUT_SECONDS` | Max wall time per AI run |
| `AI_STALE_REBUILD_PENDING_WARN` | Degraded context when rebuild backlog exceeds threshold |

## 20. Tests & CI

```bash
pip install -r requirements-dev.txt
# IMPORTANT (Windows): make sure `python` is the virtualenv interpreter.
# If you see `No module named pytest`, run tests with `.venv\\Scripts\\python`.
python -m pytest tests/unit -q

# Integration (PostgreSQL; default port 5434 — see §17)
set RUN_INTEGRATION_TESTS=true
set TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test
set SECRET_KEY=test-secret-key
alembic upgrade head
python -m pytest tests/integration -v -m integration
python -m pytest tests/integration/test_rebuild_production_guarantees.py -v
python -m pytest tests/integration/test_queue_lifecycle.py tests/integration/test_queue_backend.py -v
python -m pytest tests/integration/test_ops_api.py -v
python -m pytest tests/integration/test_orchestration_dispatch.py tests/integration/test_ai_execution.py tests/integration/test_ai_analytics_api.py -v
python -m pytest tests/unit/test_ai_providers.py tests/unit/test_ai_validation.py tests/unit/test_ai_prompt_regression.py tests/unit/test_ai_safety_controls.py -v
python -m pytest tests/unit/test_ai_governance.py tests/unit/test_rebuild_dispatcher.py -q
python scripts/architecture_governance_check.py
```

Optional stress / benchmark modules (long runtime; not run in default CI):

```bash
set RUN_STRESS_TESTS=true
pytest tests/integration/test_stress_processor.py -v -m integration
pytest tests/integration/test_inventory_rebuild_benchmark.py -v -s
```

CI (`.github/workflows/ci.yml`): Ruff, Mypy, Alembic upgrade, pytest, `docker compose config`.

### Integration testing

- Gated by `RUN_INTEGRATION_TESTS=true` and a migrated database (`public.users` must exist).
- Marked with `@pytest.mark.integration` (see `pyproject.toml`).
- WB pipeline test uses `tests/*.xlsx`; CSV-based tests use comma-delimited fixtures in `tests/integration/wb_fixtures.py` (compatible with `pd.read_csv` default delimiter).

### Test isolation model

Integration tests **commit** via `TenantSession` (RLS-aware), so savepoint rollback is not used.

**Strategy:** `TRUNCATE … RESTART IDENTITY CASCADE` before and after each integration test (`tests/integration/db_isolation.py`, autouse fixture in `tests/integration/conftest.py`).

Truncated tables include: `users`, `reports`, `etl_jobs`, financial/inventory layers, staging snapshots, consistency/anomaly quarantine, and `snapshot_rebuild_requirements`. Global `semantics_lifecycle_versions` seed data is **not** truncated.

Each test generates fresh `uuid4()` values for users, reports, and job idempotency keys — no shared static tenant IDs.

For multiple transactions in one test, prefer the `session_factory` fixture (new `AsyncSession` per block) instead of reusing one session across nested `begin()` calls.

### Deterministic test principles

1. **Empty baseline** — every integration test starts from an empty tenant/queue dataset.
2. **Unique identities** — UUIDs per entity; avoid fixed emails/checksums shared across tests.
3. **Delimiter-aware fixtures** — inline CSV fixtures use commas (not semicolons) unless the loader is extended.
4. **No ordering assumptions** — tests must pass in random order (`pytest -randomly` friendly).
5. **Schema from Alembic only** — never rely on leftover rows from manual SQL or earlier runs.

## 21. Acceptance Checklist

- [ ] `python -c "from app.main import app"`
- [ ] `ruff check` on scoped paths
- [ ] `mypy` on worker/queue/etl/domain
- [ ] `alembic upgrade head`
- [ ] `docker compose config` / `docker compose up`
- [ ] Worker processes WB report end-to-end
- [ ] Duplicate upload does not duplicate ledger rows
- [ ] Reconciliation `difference` is deterministic
- [ ] Historical cost applied by `effective_from`

## 22. API Surface

**Reports (unchanged contracts):**

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/reports/upload`
- `GET /api/v1/reports?skip=&limit=` (default `limit=200`, max `500`)
- `GET /api/v1/reports/{id}` — поля `period_start`, `period_end` (из ledger после ETL)

**Operations (read-only, additive):**

- `GET /api/v1/ops/rebuilds`
- `GET /api/v1/ops/anomalies`
- `GET /api/v1/ops/drift-checks`
- `GET /api/v1/ops/queue`
- `GET /api/v1/ops/dead-letters`
- `GET /api/v1/ops/semantics-status`

`ReportResponse.status` is projected from the latest `etl_jobs` state.

**Costs (additive):**

- `POST /api/v1/costs`
- `POST /api/v1/costs/import` / `POST /api/v1/costs/import/v2` / `POST /api/v1/costs/import/preview`
- `GET /api/v1/costs?sku=&as_of=&effective_from=&effective_to=`
- `PATCH /api/v1/costs/{id}` — обновление сумм без повторного импорта
- `GET /api/v1/costs/{id}`

**Analytics (read-only, additive):**

- `GET /api/v1/analytics/kpis/summary`
- `GET /api/v1/analytics/kpis/trends/daily`
- `GET /api/v1/analytics/kpis/top-skus`
- `GET /api/v1/analytics/kpis/period-compare`
- `GET /api/v1/analytics/kpis/abc`
- `GET /api/v1/analytics/kpis/warehouses`
- `GET /api/v1/analytics/kpis/inventory-risk`
- `GET /api/v1/analytics/coverage`

All analytics endpoints return `freshness` metadata: data-as-of, rebuild/queue state, and stale/degraded indicators.

## 23. Production Deployment Checklist

- [ ] `SECRET_KEY` rotated
- [ ] `ALLOW_LOCAL_STORAGE_FALLBACK=false`
- [ ] Supabase storage configured
- [ ] `alembic upgrade head` per release
- [ ] API and worker as separate containers
- [ ] Nginx timeouts aligned with upload size
- [ ] PostgreSQL backups enabled
- [ ] `LOG_LEVEL=INFO` or `WARNING`

## 24. Product Experience & UX Architecture

This repository is a governed analytics backend (ETL, ledgers, rebuilds, AI workflows) plus a seller-facing product frontend added in **PHASE UX-1**.

### Frontend application

Location: `frontend/`

Stack:

- React + TypeScript + Vite
- React Router (`/app/*` protected routes)
- React Query cache + retry UX
- TailwindCSS-based design primitives

#### Visual refresh (display-only, no API/backend changes)

Seller-facing UI polish: typography (Inter), calmer chart palette, unified buttons/fields, hero KPI rows, and collapsible secondary sections.

| Area | Files |
|------|--------|
| Tokens & layout | `frontend/src/styles.css`, `frontend/tailwind.config.js` |
| Formatters (≤2 decimals) | `frontend/src/utils/format.ts` |
| Charts | `frontend/src/ui/chart-theme.ts` |
| Components | `frontend/src/ui/button.tsx`, `field.tsx`, `kpi-card.tsx`, `collapsible-section.tsx`, `warn-callout.tsx`, `card.tsx` |
| Pages | `DashboardPage`, `EconomicsPage`, `SkuDrilldownPage`, `InventoryEconomicsPage`, `CostsPage`, `CostCoveragePage`, `ReconciliationPage`, `AiUsagePage`, `RecommendationsPage` |

Behavior:

- All monetary and percentage metrics render with **at most two** fractional digits (`formatMetric` / `formatRub` / `formatPct`).
- Key KPIs use `KpiCard variant="hero"` at the top of dashboard, economics, finance, and AI usage views.
- Secondary blocks (import preview, SKU tables, provider breakdown, charts) use `CollapsibleSection` (`<details>`).
- Warnings use `WarnCallout` instead of low-contrast amber-on-white text.

Details: `docs/frontend/design_system.md`.

Run (local):

```bash
cd frontend
npm install
npm run dev
```

Frontend environment (optional):

```bash
# frontend/.env.local
VITE_API_BASE_URL=http://localhost:8080
VITE_API_PREFIX=/api/v1
```

### Navigation model (route map)

- `/login`, `/register`
- `/app/onboarding`
- `/app/dashboard`
- `/app/status`, `/app/settings`, `/app/support`
- `/app/reports`, `/app/reports/upload`, `/app/reports/:reportId`
- `/app/costs`
- `/app/ai/recommendations`, `/app/ai/recommendations/:recommendationId`
- `/app/ai/runs`, `/app/ai/runs/:runId`, `/app/ai/ops`
- `/app/ops/queue`, `/app/ops/dead-letters`, `/app/ops/rebuilds`, `/app/ops/drift-checks`, `/app/ops/anomalies`
- `/app/ops/runtime/health`, `/app/ops/runtime/summary`, `/app/ops/semantics`

### Page inventory (UX-1)

- **Seller dashboard**: operational-first view of readiness, queue visibility, runtime summary, AI ops
- **Report upload**: drag/drop + progress + duplicate checksum handling + lifecycle visibility
- **Analytics exploration**: **partially blocked** (see “Missing APIs”) — backend metric models exist but read endpoints are not yet exposed
- **AI recommendations**: actionable list + detail with explainability payload + operator feedback recording
- **Operational visibility (read-only)**: queue, rebuild lifecycle, drift checks, anomalies, dead letters, runtime health/summary, semantics status

### Onboarding & real seller workflows (UX-2)

UX-2 adds seller-oriented onboarding and workflow realism without changing backend invariants.

- **Onboarding wizard**: `/app/onboarding` (progressive disclosure setup)
- **Costs workflow**: `/app/costs` (cost import to enable profitability)
- **AI usefulness UX**: recommendation detail includes “Why this matters”, suggested action, and usefulness rating → feedback API
- **Real data validation**: script + small fixtures under `docs/product/`

Product documentation (UX-2):

- `docs/product/onboarding.md`
- `docs/product/seller_workflows.md`
- `docs/product/real_data_validation.md`
- `docs/product/usability_audit.md`
- `docs/product/ai_usefulness.md`

### Frontend state model

Layering (simplified):

- `src/state/http.ts`: API client, base URL, JWT auth header
- `@tanstack/react-query`: server-state cache, retries, stale-time
- Route-level error boundaries: keep app shell stable on rendering errors

### Screenshots / diagrams

For UX-1, diagrams are provided as Mermaid route maps in:

- `docs/frontend/frontend_architecture.md`

### Documentation

Frontend UX documentation:

- `docs/frontend/frontend_architecture.md`
- `docs/frontend/user_workflows.md`
- `docs/frontend/design_system.md`
- `docs/frontend/dashboard_model.md`
- `docs/frontend/ai_user_experience.md`

### Missing APIs / UX blockers (documented)

Requested seller KPIs (revenue/profit/margin, top SKUs, trends) require read endpoints that are not currently present in `app/api/*`.
The backend already defines metric models (e.g. `MetricResponse` in `app/schemas/catalog.py`), but UX-1 does **not** invent new backend semantics.

## 25. MVP Productization (UX-3)

UX-3 prepares the platform for **controlled external usage** as an MVP product: trust, polish, demo readiness, and explicit maturity boundaries — without redesigning backend invariants.

### MVP readiness summary

| Dimension | Score | Status |
|-----------|-------|--------|
| MVP readiness | 6.5 / 10 | Upload + AI advisory ready; KPI APIs missing |
| Production readiness | 5.5 / 10 | Backend mature; product needs auth recovery + server settings |
| AI usefulness | 6.0 / 10 | Feedback loop + transparency; explainability UX pending |
| UX maturity | 6.5 / 10 | Onboarding + trust banners; reduce raw JSON exposure |

Full audit: [docs/product/mvp_readiness.md](docs/product/mvp_readiness.md)

### Trust & transparency (implemented)

- **Global trust banners** in app shell (rebuilds, queue, failed uploads, AI cautious mode)
- **System status** page: `/app/status` (plain-language, no raw JSON required)
- **AI transparency notice** on recommendation detail
- **Settings** alert preferences (stale data, rebuilds, AI degraded)

Details: [docs/product/trust_and_transparency.md](docs/product/trust_and_transparency.md)

### MVP operational workflows (implemented)

| Feature | Route | Storage |
|---------|-------|---------|
| Tenant settings | `/app/settings` | Local (until server API) |
| System status | `/app/status` | Live API |
| Support & debug | `/app/support` | Tenant context + local usage |
| Report history + filters | `/app/reports` | API + saved views (local) |
| AI recommendation history | `/app/ai/recommendations` | API |
| Usage tracking | Support page | Local events |
| Product mode (MVP/demo/full) | Settings | Local |

MVP mode **hides internal ops pages** from navigation by default.

### Demo & portfolio readiness

- Demo mode toggle in Settings or `VITE_PRODUCT_MODE=demo`
- 15-minute walkthrough script
- Validation harness: `scripts/ux2_real_data_validation.py`

Guide: [docs/product/demo_environment.md](docs/product/demo_environment.md)

### Product maturity & roadmap

Gap analysis, top-10 priorities, and known limitations:

- [docs/product/product_maturity.md](docs/product/product_maturity.md)

### UX-3 documentation index

- `docs/product/mvp_readiness.md` — maturity classification, blockers, scores
- `docs/product/demo_environment.md` — demo tenant, walkthrough, showcase
- `docs/product/trust_and_transparency.md` — trust UX model
- `docs/product/product_maturity.md` — gap analysis and roadmap

### Recommended next milestones (critical)

1. Metrics read APIs → KPI dashboard widgets
2. SKU mapping CRUD + UI
3. Seller-friendly explainability rendering
4. Password recovery + server-side tenant settings

## 26. Analytics Read Layer & Seller KPI APIs (ANALYTICS-1)

ANALYTICS-1 adds a governed **analytics read layer** on top of existing ledger-derived projections, exposing seller KPI APIs and wiring the dashboard to real revenue/profit/trend/top-SKU data.

### Read layer architecture

- **Authoritative**: append-only ledgers
- **Derived projections** (rebuildable): `daily_aggregates`, `sku_daily_metrics`, `warehouse_stock_snapshots`
- **Dashboard read models**: KPI DTOs returned by `/api/v1/analytics/*`

Docs:

- `docs/analytics/read_layer.md`
- `docs/analytics/kpi_catalog.md`
- `docs/analytics/dashboard_queries.md`
- `docs/analytics/analytical_consistency.md`
- `docs/analytics/seller_metrics.md`
- `docs/analytics/financial_semantics.md`
- `docs/analytics/integrity_validation.md`
- `docs/analytics/report_coverage.md`
- `docs/analytics/marketplace_accounting.md`

### Freshness model (explicit)

All KPI endpoints return `freshness`:

- `data_as_of` (max aggregate date)
- rebuild/queue state (from runtime summary)
- `stale_data_warning` and `degraded_mode` flags

### Financial Integrity & Marketplace Accounting (FINANCIAL-INTEGRITY)

This phase prioritizes **seller financial truthfulness** and prevents impossible KPI relationships.

- **Payout is not profit**: payout is cash settlement; profit is P&L. Payout is excluded from profit aggregation.
- **Integrity warnings (deterministic)**: analytics responses include `integrity.warnings[]`.
- **Coverage API**: `GET /api/v1/analytics/coverage` reports periods, gaps, uploaded report types, recommendations, and warnings.

### Seller Analytical UX & Period Intelligence (SELLER-UX)

- Global selector for **period + comparison**
- Seller dashboard shows **period-aware KPIs**, trends, completeness, and integrity warnings
- Coverage-driven UX: missing periods and “what to upload next” recommendations

Docs:

- `docs/frontend/period_analytics_ux.md`
- `docs/frontend/analytics_comparison.md`
- `docs/frontend/analytical_transparency.md`
- `docs/frontend/localization.md`
- `docs/frontend/seller_dashboard.md`

## SKU Economics & Seller Profitability (ECONOMICS-1)

This phase adds a deterministic seller economics layer:

- **Projection**: `sku_unit_economics_daily` (rebuildable; never mutates ledger history)
- **API**: `GET /api/v1/analytics/sku-economics` (period-aware, sortable, paginated)
- **Profitability**: contribution margin derived from governed fee ops + effective-dated COGS (`cost_history`)
- **Trust**: every response includes `freshness` + `integrity` warnings; missing-cost limits are explicit

Docs:

- `docs/economics/sku_unit_economics.md`
- `docs/economics/inventory_economics.md`
- `docs/economics/profitability_model.md`
- `docs/economics/marketplace_cost_model.md`
- `docs/economics/economics_validation.md`

## Marketplace Reconciliation & Cost Intelligence (ECONOMICS-2)

- **Cost coverage intelligence**: `GET /api/v1/analytics/cost-coverage`
- **Reconciliation** (period): `GET /api/v1/analytics/reconciliation/period`
- Seller-facing trust signals: missing COGS, outdated costs, duplicate imports, payout mismatches

Docs:

- `docs/economics/reconciliation_model.md`
- `docs/economics/cost_coverage.md`
- `docs/economics/financial_confidence.md`

## Seller Daily Operating System (OPERATING-SYSTEM)

This phase turns the product into a daily seller workspace:

- Dashboard organized around: **“Что требует внимания сегодня?”**
- Daily briefing page: `GET /app/today`
- Prioritization tiers: do today / this week / informational (deterministic, trust-aware)
- Explainability and trust indicators surfaced across recommendations and dashboards

Docs:

- `docs/product/daily_operating_system.md`
- `docs/product/seller_prioritization.md`
- `docs/product/daily_digest.md`
- `docs/product/operational_ai.md`
- `docs/product/trust_experience.md`

### Dashboard integration

The dashboard now renders:

- revenue/profit/margin summary
- revenue + profit daily trend chart
- top SKUs table with contribution %

## 27. AI Usefulness & Recommendation Quality (AI-USEFULNESS)

This phase improves AI **usefulness, clarity, actionability, and trust** without adding orchestration, agents, or infrastructure.

### What’s implemented

- **Recommendation quality engine** (post-processing, read-only inputs):
  - confidence normalization under stale/no-evidence/generic/contradiction conditions
  - explicit seller-facing fields stored in `action_plan`: `why_this_matters`, `recommended_action`, `impact_estimate`
  - stable **fingerprint** in `lineage` for repetition grouping
  - duplicate suppression by fingerprint (reduces fatigue)
- **Feedback loop metrics**:
  - `GET /api/v1/ai/recommendations/stats` (avg rating, helpful/accept/reject rates, ignored-after-7d, fatigue proxy)
- **Explainability UX upgrades**:
  - evidence nodes rendered as readable items; reasoning trace remains available for deep inspection

### Docs

- `docs/ai/recommendation_quality.md`
- `docs/ai/ai_usefulness_report.md`
- `docs/ai/explainability_ux.md`
- `docs/ai/recommendation_feedback.md`
- `docs/ai/ai_product_value.md`

## 28. Product Validation & Real Seller Workflows (PRODUCT-VALIDATION)

This phase validates the platform as a **real working seller product** using realistic workflows, data profiles, friction analysis, and readiness scoring — without architecture expansion.

### Workflow simulation

Four seller workflows simulated (API + UI mapped):

| Workflow | Status |
|----------|--------|
| **Daily** (upload → KPIs → anomalies → AI) | UI-complete |
| **Weekly** (period compare, ABC, warehouse risk) | API-complete; **UI gap** |
| **Incident** (broken report, stale data, suspicious AI) | Partial — System Status strong, ops JSON weak |
| **Growth** (top SKUs, margin, stock optimization) | Dashboard partial; API-complete |

Harness: `scripts/product_validation_simulation.py`

```bash
python scripts/product_validation_simulation.py --workflow all
```

### Product validation results (scores / 10)

| Dimension | Score |
|-----------|-------|
| Seller usability | 7.0 |
| Analytics usefulness | 7.0 |
| AI usefulness | 6.5 |
| Workflow clarity | 6.5 |
| Trust/transparency | 7.5 |
| Operational maturity (seller-facing) | 7.0 |
| Demo readiness | 7.0 |
| **MVP readiness** | **7.0** |

**Composite: 6.9 / 10** — controlled external MVP viable; weekly analysis UI is top blocker.

### MVP blockers (refined)

1. Weekly Analysis UI (period compare, ABC, inventory risk)
2. SKU mapping CRUD + UI
3. Password recovery
4. Costs-import nudge when margin KPIs shown without costs

### Docs

- `docs/product/workflow_simulation.md`
- `docs/product/real_seller_scenarios.md`
- `docs/product/product_validation.md`
- `docs/product/ux_friction_report.md`
- `docs/product/refined_roadmap.md`

## 29. Real AI Provider Runtime (REAL-AI-1)

This phase integrates a real **OpenAI-compatible** provider while preserving governance, RLS isolation, auditability, and advisory-only guarantees.

### Configuration

- `AI_PROVIDER` = `mock` | `openai_compatible`
- `AI_FAILOVER_PROVIDER` (optional)
- `AI_OPENAI_BASE_URL`
- `AI_OPENAI_API_KEY`
- `AI_OPENAI_MODEL`
- `AI_REQUEST_TIMEOUT_SECONDS`
- `AI_MAX_RETRIES`

### Runtime execution + audit

- Runs are persisted in `ai_execution_runs` and completed via `AIOrchestrationService`.
- Token/cost fields persisted per run: `provider_name`, `model_name`, `prompt_tokens`, `completion_tokens`, `estimated_cost`.
- Usage API: `GET /api/v1/ai/usage`

### Streaming

- Backend SSE endpoint: `POST /api/v1/ai/runs/stream`
- Frontend demo UI: Streaming panel on `/app/ai/recommendations`

### Docs

- `docs/ai/current_prompt_runtime.md`
- `docs/ai/provider_integration.md`
- `docs/ai/prompt_runtime_architecture.md`
- `docs/ai/runtime_execution.md`
- `docs/ai/streaming_architecture.md`
- `docs/ai/cost_tracking.md`

## 30. Multi-Layer AI Intelligence (REAL-AI-2)

Transforms single-stage LLM recommendations into a **structured multi-layer architecture** while preserving deterministic KPI authority, advisory-only AI, auditability, and explainability.

### Architecture

```
AIInsightInputDTO (deterministic KPIs)
  → AnalyticalIntelligencePackage
  → 6× Domain Analyst (structured JSON findings)
  → ExecutiveIntelligenceAggregator
  → enrich recommendation + reasoning_trace
```

Domain analysts **never compute raw metrics** from source reports; they reason only over governed slices (`SalesAnalyticsSlice`, `AnomalyAnalyticsSlice`, etc.).

### Domain analysts

| Analyst | Contract |
|---------|----------|
| Sales | `analyst.sales.v2` |
| Ads | `analyst.ads.v2` |
| Funnel | `analyst.funnel.v2` |
| Inventory | `analyst.inventory.v2` |
| Marketplace comparison | `analyst.marketplace.v2` |
| Anomaly | `analyst.anomaly.v2` |

Code: `app/ai/analysts/`, orchestration: `app/ai/analysts/orchestrator.py`

### Executive intelligence

`ExecutiveIntelligenceAggregator` merges domain outputs, resolves contradictions, prioritizes by severity × confidence, estimates business impact, and builds seller-facing narrative. Contract: `executive.aggregate.v2`.

### Prompt contracts v2

Registry: `app/ai/prompts/contracts_v2/registry.py` — versioned input/output schemas, evaluation examples, metadata per analyst.

### Reasoning lifecycle

Persisted in `ai_recommendations.reasoning_trace`:

- `multi_layer.domain_outputs`
- `multi_layer.executive` (aggregation, conflicts, confidence propagation)
- `domain_insights` (UI-ready prioritized findings)

### Evaluation

`app/ai/evaluation/multi_layer_suite.py` — contract registration, schema checks, contradiction/stale/low-confidence tests. Unit tests: `tests/unit/test_multi_layer_intelligence.py`.

### Docs

- `docs/ai/prompt_topology_analysis.md`
- `docs/ai/domain_analysts.md`
- `docs/ai/executive_intelligence.md`
- `docs/ai/prompt_contracts_v2.md`
- `docs/ai/reasoning_pipeline.md`
- `docs/ai/recommendation_generation.md`

### Frontend

Recommendation detail shows per-analyst insights: label, confidence, severity, evidence refs, priority rank, and reasoning summary (`domain_insights` in explainability trace).

## 31. Seller-Facing AI Productization (REAL-AI-3)

Turns technical recommendations into a **seller assistant** focused on usefulness, clarity, trust, and actionable workflows.

### Seller usefulness model

Every intelligence recommendation persists `action_plan.seller_usefulness`:

- why_this_matters, expected_business_impact, urgency
- estimated_upside / estimated_downside
- concrete_next_action, confidence_explanation, limitations

Built in `app/ai/product/seller_usefulness.py` via `apply_quality()`.

### Seller workflows

| Action | Endpoint |
|--------|----------|
| Complete / save / snooze / dismiss | `PATCH /api/v1/ai/recommendations/{id}/workflow` |
| Inbox filter | `GET /ai/recommendations?group=inbox` |
| Priority grouping | Frontend inbox (high / medium / low) |

DB: `seller_workflow_state`, `snoozed_until` (migration `0020_seller_ai_workflows`).

### AI digests

- `GET /api/v1/ai/digests/daily`
- `GET /api/v1/ai/digests/weekly`
- `GET /api/v1/ai/digests/anomaly`

UI: `/app/ai/digest`

### Conversational UX (explainable, not autonomous)

- `POST /api/v1/ai/recommendations/{id}/ask` — deterministic answers from stored trace/plan
- Detail page chips: why · impact · action · confidence · evidence · limitations

### Trust & transparency

- Explainability `trust_context` (limitations, stale notes, advisory-only)
- `AiTrustPanel` on recommendation detail
- No generic GPT filler; answers cite `sources[]`

### Usefulness analytics

- `GET /api/v1/ai/usefulness/metrics` — acceptance, ignored, fatigue, conversion rate
- Extended `GET /api/v1/ai/recommendations/stats`

### Validation

```bash
python scripts/seller_ai_validation.py
pytest tests/unit/test_seller_ai_product.py -q
```

Scenarios: strong/weak store, stockout, ads overspend (limited data), declining conversion anomaly, export-shaped KPIs.

### Docs

- `docs/product/ai_ux_audit.md`
- `docs/product/ai_assistant_workflows.md`
- `docs/product/recommendation_lifecycle.md`
- `docs/product/ai_trust_model.md`
- `docs/product/ai_usefulness_metrics.md`

## 32. Real AI Runtime & Prompt System V3 (REAL-AI-V4A)

Production-grade LLM execution on top of the existing governed stack (RLS, audit runs, advisory-only, deterministic KPI boundaries unchanged).

### Provider setup

See `docs/ai/provider_setup.md`. OpenAI-compatible providers: OpenAI, OpenRouter, DeepSeek, Together, Ollama (`AI_PROVIDER` + `AI_OPENAI_*` / `AI_FAILOVER_*`).

### Model routing

`app/ai/providers/model_router.py`:

| Role | Use |
|------|-----|
| `REASONING` | Causal, risk, anomaly, executive workflows |
| `FAST` | Streaming, short summaries |
| `CHEAP` | Lightweight / embedding path |

Env: `AI_REASONING_MODEL`, `AI_FAST_MODEL`, `AI_CHEAP_MODEL` (fallback: `AI_OPENAI_MODEL`).

### Prompt runtime v3

`app/ai/prompts/v3/` — analytical contracts (not chat prompts). Structured JSON output with why, impact, urgency, actions, evidence_refs, limitations.

```env
AI_PROMPT_RUNTIME_VERSION=v3
```

Registry supports **active/inactive** prompts, labels, and `rollback_target` to v1 ids.

### Failover & degradation

`app/ai/providers/failover.py`: primary → failover → mock. Health in `app/ai/providers/health.py`; circuit breaker integration; events in `audit_events` / `runtime_metadata`.

### Streaming & cost governance

- `AI_ENABLE_STREAMING` — SSE runs
- `AI_ENABLE_COST_TRACKING` — per-run and daily USD caps (`AI_MAX_COST_PER_RUN_USD`, `AI_MAX_COST_PER_DAY_USD`)
- Optional `AI_ENABLE_RESPONSE_CACHE` + `AI_CACHE_TTL_SECONDS`

### APIs

- `GET /api/v1/ai/costs` — workflow/prompt/provider breakdown, expensive runs
- `GET /api/v1/ai/providers/status` — health + estimated monthly cost
- `GET /api/v1/ai/usage` — token totals

### UI

`/app/ai/usage` — AI usage panel (cost caps, provider health).

### Evaluation

`docs/ai/prompt_evaluation.md` — stale data, unsupported claims, usefulness, governance rules.

```bash
pytest tests/unit/test_prompt_v3_runtime.py tests/unit/test_ai_failover_v4.py -q
```

### Operational constraints

- AI never becomes financial authority; validates against governed `metrics_snapshot`
- Cost caps block runs (policy violation), no ledger mutation
- Mock degradation when credentials missing or circuit open
- `runtime_metadata` on `ai_execution_runs` stores provider, model role, failover, v3 prompt id

Migration: `0021_ai_runtime_v3_metadata` (`runtime_metadata` JSONB).

## 33. Seller Intelligence & AI Usefulness (REAL-AI-V4B)

Transforms recommendations into a **daily seller assistant** with actionable fields, impact ranges, prioritization, and fatigue control.

### Actionable recommendations

Every recommendation persists full `action_plan.seller_usefulness` (via `build_actionable_payload`):

- why_this_matters, expected_business_impact, urgency, root_cause, what_changed
- what_to_do_today, recommended_action, estimated_effort, expected_outcome
- confidence_explanation, measurable_impact (ranges only), prioritization, novelty_score

Code: `app/ai/product/seller_intelligence.py`, integrated in `app/ai/quality/recommendation_quality.py`.

### Measurable impact

`app/ai/product/impact_estimation.py` — revenue recovery, margin, stockout, ad waste **bands** with evidence refs and uncertainty notes. No fabricated exact amounts (`do_not_trust_exact_amounts`).

### Prioritization engine

`app/ai/product/prioritization.py`:

| Tier | When |
|------|------|
| `today` | score ≥ 72 or urgency ≥ 80 |
| `this_week` | score ≥ 48 or urgency ≥ 55 |
| `informational` | otherwise |

Stored in `lineage.priority_tier` and inbox UI grouping.

### Daily seller assistant

- `GET /api/v1/ai/todays-focus` — Today's Focus briefing
- UI: `/app/ai/today` (priority queue, top 3 actions, critical alerts, quick wins)
- Links from inbox and dashboard

### Fatigue reduction

`app/ai/product/fatigue.py` — cooldown, decay, duplicate suppress (≥4 repeats / 7d), novelty scoring. Wired in `AIIntelligenceEngine` before persist.

### Usefulness evaluation

Extended `GET /api/v1/ai/usefulness/metrics`:

- usefulness_score, repeated_dismissals, feedback_trend

Framework: `docs/ai/usefulness_framework.md`

### Validation

```bash
pytest tests/unit/test_seller_intelligence_v4b.py tests/unit/test_seller_ai_product.py -q
pytest tests/unit -q
ruff check .
mypy app tests
cd frontend && npm run build
```

### Seller workflows

1. Open **Today's Focus** → scan top actions and critical alerts
2. Work **inbox** by tier (today / this week / informational)
3. Open detail → evidence, impact ranges, ask follow-ups
4. Complete / dismiss / snooze → feeds usefulness metrics

### Recommendation lifecycle

Generate → quality + fatigue → prioritize → persist (dedupe/suppress) → Today's Focus + inbox → workflow + feedback → usefulness analytics.

## 34. Local Runtime Testing

Run the full platform locally for **manual seller QA** with real marketplace uploads and optional **real OpenAI-compatible** LLM calls.

**Primary guide:** [`docs/testing/local_runtime_testing.md`](docs/testing/local_runtime_testing.md)

### Quick start

```powershell
copy .env.example .env
# Edit: SECRET_KEY, AI_PROVIDER=openai, AI_OPENAI_API_KEY, STORAGE_BACKEND=local

.\scripts\local\start-all.ps1

cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

| URL | Service |
|-----|---------|
| http://localhost:8080 | API (nginx) |
| http://localhost:8080/health | Liveness |
| http://localhost:5173 | Frontend (Vite) |

### Convenience scripts

| Script | Purpose |
|--------|---------|
| `scripts/local/start-all.ps1` / `.sh` | Docker compose up + health wait |
| `scripts/deploy-frontend.sh` | RAM-safe build + publish to `/var/www/marketplace-analytics` |
| `scripts/install-frontend-ops.sh` | systemd units + daily cleanup timer |
| `scripts/cleanup-frontend-artifacts.sh` | trim npm/vite cache and logs |
| `scripts/local/start-dev-no-docker.sh` | API :8000 + Vite :5173 без Docker |
| `scripts/local/stop-all.ps1` / `.sh` | `docker compose down` |
| `scripts/local/reset-db.ps1` / `.sh` | Wipe volumes + migrate + restart |
| `scripts/local/run-local-smoke-test.py` | Health, auth, ops/AI status |

### Manual QA flow (summary)

1. Register / login
2. Upload WB `.xlsx` → wait for worker (`processed`)
3. Dashboard KPIs
4. AI intelligence → inbox + Today's Focus
5. Workflow + usefulness metrics
6. Verify `GET /api/v1/ai/providers/status` (not `mock` when testing real LLM)

### Real AI testing

```env
AI_PROVIDER=openai
AI_OPENAI_API_KEY=sk-...
AI_PROMPT_RUNTIME_VERSION=v3
AI_ENABLE_STREAMING=true
```

Docker services load `.env` via `env_file` on `api`, `worker`, and `orchestrator`. Startup logs warn if `AI_PROVIDER=mock` while a key is set.

### Expected local architecture

`postgres` + `migrate` + `api` + `worker` + `orchestrator` + `nginx` — see diagram in `docs/testing/local_runtime_testing.md`. Governance (RLS, advisory AI, governed metrics) is unchanged locally.


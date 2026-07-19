# Phase 9.17-B — Upload status UX audit (no implementation)

**Mode:** Audit only · do not change FE labels in this phase

## 1. Statuses visible to the seller today

| Surface | What the user sees |
|---------|-------------------|
| Upload page | Button «Загрузить» / «Загрузка…» while HTTP upload runs |
| Reports list | Raw backend status string via `StatusBadge`: `pending`, `processing`, `processed`, `failed` (filter labels: В обработке / Готово / Ошибка) |
| Report detail | Same badge + optional `job.status` hint + `processed_at` |
| Error path | `error_hint` / `error_message` when failed |
| Analytics | No stage progress — data appears when report is `processed` and aggregates exist |

There is **no** multi-step progress bar for Parse → Ledger → Inventory → Aggregates.

## 2. Actual backend stages (worker)

| Stage | Typical signal | Maps to report status |
|-------|----------------|------------------------|
| Upload + checksum + enqueue | HTTP 201 | `pending` (job queued) |
| Claim job | worker | `processing` |
| Parse / stream | `process_wb_streamed` | `processing` |
| Phase 1 ledger persist | `persist_phase1` | `processing` |
| Phase 2 inventory rebuild | `InventorySnapshotRebuildService` | `processing` |
| Phase 3 daily/SKU aggregates | `_rebuild_aggregates` | `processing` |
| ACK | `ack_job` | **`processed`** — dashboard ready |
| Post-report AI hook | `maybe_generate_recommendation_after_report` | Does **not** change report status; **no-op by default** (9.17-B) |

Lifecycle source of truth: `etl_jobs` via `derive_report_status()` (report.status column is not authoritative for writes).

## 3. Recommended seller-facing progress model

| Step | Seller label | Backend |
|------|--------------|---------|
| 1 | Загрузка отчёта | Upload HTTP |
| 2 | Обработка операций | Parse + Phase 1 ledger |
| 3 | Построение аналитики | Phase 2 inventory + Phase 3 aggregates |
| 4 | Аналитика готова | `processed` / ACK |
| 5 (optional, separate) | AI-анализ (по кнопке) | Explicit «Запустить анализ» only |

### UX notes (for a future phase)

- Collapse `pending` + early `processing` into step 2 once the worker claims the job.
- Do **not** imply AI is running during ETL.
- After step 4, CTA: «Открыть аналитику» and separately «Запустить AI-анализ».
- Long Phase 3 windows (minutes) should show an honest «это может занять несколько минут» under step 3 — that is the real bottleneck (see ETL audit).

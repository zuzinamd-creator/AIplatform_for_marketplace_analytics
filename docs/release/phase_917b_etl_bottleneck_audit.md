# Phase 9.17-B — ETL bottleneck audit

**Mode:** Audit (paired with Auto-AI disable) · evidence from production worker logs 2026-07-19  
**Product SHA context:** post–9.16-C baseline

## Timeline (upload → dashboard)

| Stage | Code | Dashboard blocked? |
|-------|------|--------------------|
| Upload + checksum | `upload_report` / `buffer_upload_with_checksum` | No (enqueue) |
| Upload validate parse | `validate_report_file` | Upload only |
| Queue claim | `marketplace-worker` | Yes until done |
| Parse / stream | `process_wb_streamed` / `etl_process_content` | Yes |
| Phase 1 ledger writes | `persist_phase1_chunk` / phase1 | Yes |
| Phase 2 inventory rebuild | `InventorySnapshotRebuildService.rebuild` | Yes |
| Phase 3 aggregates | `_rebuild_aggregates` | Yes |
| ACK → `processed` | `ReportService.ack_job` | **KPIs available** |
| Post-report AI hook | `maybe_generate_recommendation_after_report` | No for KPIs (9.17-B: no-op by default) |

## Measured production samples (2026-07-19)

| Job | Rows | Parse | Persist (+ rebuild) | Auto AI |
|-----|------|-------|---------------------|---------|
| A | 30 | 8.3 s | **825 s** (rebuild ~820 s, window 2026-07-06..12) | ~11 s (pre-disable) |
| B | 4032 | 68.8 s | **311 s** (rebuild ~112 s) | ~10 s (pre-disable) |

**Dominant bottleneck:** Phase 2/3 rebuild path inside `etl_persist_result`, not AI.

## Top bottlenecks

| # | Issue | Location | Est. improvement if fixed |
|---|--------|----------|---------------------------|
| 1 | **Full ledger reload for all affected dates** then purge+recompute daily/SKU/unit-econ | `persist_aggregates._rebuild_aggregates` / `_load_ledger_drafts_for_dates` | High (minutes → tens of seconds for narrow windows) |
| 2 | **Inventory window rebuild** under advisory lock | `InventorySnapshotRebuildService` | High when window large / contended |
| 3 | **Remote DB RTT** (many sequential queries) | Supabase from VPS | Medium–High (batching / fewer round-trips) |
| 4 | Upload-time **full re-parse** before enqueue | `validate_report_file` | Medium on large xlsx |
| 5 | Single worker serial queue | `marketplace-worker` | Medium under concurrent uploads |
| 6 | ~~Post-ETL auto AI~~ | `post_report_ai` | **Mitigated in 9.17-B** (~10–14 s / job + tokens) |
| 7 | Cost snapshot full-table load | `load_cost_snapshots` | Low–Medium |
| 8 | Repeated phase row-count asserts | persist layers | Low |

## Patterns found

- **Full-window rebuild (by design):** for multi-report correctness on shared dates — expensive but intentional.  
- **Not incremental merge:** delete SKU/daily for dates then rebuild from ledger.  
- **Blocking:** phases run sequentially in one worker job.  
- **N+1 risk:** less in aggregate rebuild (bulk select by dates); more in dashboard/coverage (separate audit).

## Optimization candidates (future phases — not implemented here)

1. Incremental aggregate update for *new* report rows when date has no prior conflicting reports.  
2. Parallel Phase 2 / Phase 3 where safe.  
3. Persist timing spans per phase in metrics (`phase1_ms`, `phase2_ms`, `phase3_ms`).  
4. Skip upload full parse; defer validation to worker.  
5. Dedicated AI worker (even if auto remains off).

## UX status mapping (audit only)

| Backend | Typical seller label today | Recommended label |
|---------|----------------------------|-------------------|
| upload HTTP | Uploading | Загрузка отчёта |
| job `pending`/`processing` + parse/phase1 | `processing` | Обработка операций |
| phase2+phase3 rebuild | still `processing` | Построение аналитики |
| `processed` / ACK | `processed` | Аналитика готова |
| AI (manual) | separate AI page | AI-анализ (по кнопке) |

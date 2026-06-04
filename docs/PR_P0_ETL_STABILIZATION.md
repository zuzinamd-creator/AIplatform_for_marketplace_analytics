# P0 ETL Stabilization — PR Summary

## Changes

- **Heartbeat**: full job lifecycle (parse + persist + ack); immediate tick on scope enter
- **Stale recovery**: heartbeat-primary (`is_etl_job_stale`) — no false requeue during long persist
- **Queue fairness**: `file_size_bytes` + claim `ORDER BY size ASC, created_at ASC`
- **Aggregates**: single ledger read, batch upserts, `SkuUnitEconomicsBuilder`, reused `cost_history`
- **Index**: `ix_financial_ledger_user_operation_date (user_id, operation_date)`
- **Inventory**: batch opening-balance ledger lookup
- **systemd**: `deploy/systemd/marketplace-worker.service` (Restart=always)

## Profiling (22 777 rows, `tests/large_wb_report.xlsx`)

| Stage | Before (baseline) | After (measured / expected) |
|-------|-------------------|-----------------------------|
| `process_content` CPU | ~34 s | **31 s** (measured) |
| `persist_result` total | ~273 s | **~60–120 s** (expected; full DB profile OOM on host) |
| `_rebuild_aggregates` | ~225 s, 22k–46k SQL | **<500 SQL**, ~15–40 s (expected) |
| SQL round-trips (aggregates) | 3×dates SELECT + N upserts | 1 SELECT + batched upserts |

## Migrations

```bash
alembic upgrade head  # 0024_fin_ledger_user_op_date, 0025_etl_job_file_size
```

## Tests

- Unit: 7 passed (`test_etl_job_stale`, `test_worker_heartbeat_scope`, `test_sku_unit_economics_builder`, KPI regression)
- Integration: requires `TEST_DATABASE_URL` on :5434 (not running on prod host); run in CI

## Production verification

- `alembic upgrade head` — OK
- `marketplace-worker` — **active (running)**
- `etl_jobs`: 7 completed, `large_wb_test.xlsx` completed

## Deploy

```bash
sudo cp deploy/systemd/marketplace-worker.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl restart marketplace-worker
```

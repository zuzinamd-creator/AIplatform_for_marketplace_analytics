# Performance budgets

Governance targets for inventory rebuild and queue throughput. **Not CI gates by default** — validate with `RUN_STRESS_TESTS=true` and benchmark integration tests.

## Rebuild duration

| Workload | Mode | Budget (p95) | Notes |
|----------|------|--------------|-------|
| ≤ 10k ledger rows | incremental | < 30 s | Typical daily persist path |
| ≤ 10k ledger rows | full | < 90 s | Staging + promote |
| 50k ledger rows | full | < 600 s | `test_inventory_rebuild_benchmark.py` |
| 50k ledger rows | incremental | within 2× of full on same hardware | Equivalence test, not wall-clock SLA |

**Warning:** `ops_rebuild_duration_high` when `rebuild_duration_ms > OPS_REBUILD_DURATION_WARN_MS` (default 120_000).

## Memory envelope

| Path | Budget |
|------|--------|
| Full rebuild stream | Peak RSS < 512 MB above baseline for 50k rows (benchmark assertion) |
| Incremental rebuild | Bounded by window + batch upsert; no full ledger materialization in Python |

## WAL expectations

| Operation | Budget |
|-----------|--------|
| Full promote (50k rows) | WAL delta < `OPS_WAL_BYTES_DELTA_WARN` (default 500 MB) per tenant run |
| Incremental upsert day | Proportional to changed SKUs; no delete-all |

Measure: `SELECT wal_bytes FROM pg_stat_wal` before/after (benchmark script or `ProductionSafetyGuards.read_wal_bytes()`).

## Queue throughput

| Metric | Budget |
|--------|--------|
| Claim → ack (WB report, median) | < 5 min for standard file sizes |
| Oldest `pending` age | < `OPS_QUEUE_LAG_WARN_SECONDS` (default 1800 s) |
| Visibility recovery | Stale jobs recovered within one worker loop + timeout window |

Worker must call `recover_stale()` each iteration (invariant Q-VIS-RECOVER).

## Contention

| Resource | Budget |
|----------|--------|
| Advisory rebuild lock | ≤ 1 holder per tenant |
| Concurrent workers per tenant | Many jobs OK; **one inventory rebuild** at a time |
| `SKIP LOCKED` claim collisions | Expected under load; zero blocked workers |

## Anomaly & drift rates (health, not latency)

| Signal | Budget |
|--------|--------|
| Anomalies / 24 h / tenant | < `OPS_ANOMALY_COUNT_WARN` (500) |
| Failed drift checks / 24 h | < `OPS_DRIFT_FAIL_WARN` (50) |

## Regression process

1. `RUN_STRESS_TESTS=true pytest tests/integration/test_inventory_rebuild_benchmark.py`
2. Compare `rebuild_duration_ms`, `snapshot_rows_written`, WAL delta in logs
3. Update this document if hardware class changes

See [release_checklist.md](release_checklist.md) for release-time validation.

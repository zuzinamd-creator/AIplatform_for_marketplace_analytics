# Alerting model

Log-based alerting assumptions (no Prometheus rules in-repo yet). Tune thresholds per environment after baseline.

## Critical alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| `DeadLetterSpike` | `dead_letter` jobs > N/hour per tenant | Inspect `last_error`; fix data or requeue |
| `RebuildFailedExhausted` | `orchestration_status=failed` on rebuild requirements | Manual full rebuild playbook |
| `DriftCritical` | `is_consistent=false` drift checks increasing | Run drift recovery playbook |
| `AnomalyPersistDown` | `etl_anomaly_persist_failed` sustained | DB/RLS issue; ledger may be OK |
| `WorkerStopped` | No `job_claimed` logs > 10m while pending jobs exist | Restart worker container |

## Warning alerts

| Alert | Condition | Action |
|-------|-----------|--------|
| `AdvisoryLockContention` | `advisory_lock_contention` rate high | Scale time-between-retries; avoid parallel rebuild triggers |
| `QueueLag` | Oldest `pending` job age > 30m | Scale workers; check DB load |
| `StaleProcessing` | `processing` jobs with old `claimed_at` until recover runs | Verify `recover_stale` in worker loop |
| `InvariantViolation` | `platform_invariant_violation` any | Investigate promote mismatch / duplicate drafts |
| `SemanticsDeprecatedIngest` | `SEMANTICS_INGEST_BLOCKED` anomalies | Plan version migration |

## Rebuild SLA thresholds (guidance)

| Tenant size | Incremental rebuild p95 | Full rebuild |
|-------------|-------------------------|--------------|
| <10k ledger rows | <30s | <60s |
| ~50k rows | <20s (reference benchmark) | <90s |
| >100k rows | Establish baseline via `RUN_STRESS_TESTS` | Schedule off-peak |

SLAs are **not enforced** automatically — use benchmark output + logs.

## Escalation paths

1. **L1:** ops API `/ops/*` — queue, anomalies, drift, rebuilds  
2. **L2:** SQL tenant-scoped queries + `disaster_recovery.md` playbooks  
3. **L3:** Engineering — ADR/invariant breach, migration rollback  

## Notification channels (out of scope)

Wire log alerts to your platform (CloudWatch, Loki, Datadog, etc.) using event names above.

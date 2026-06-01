# Invariant Validation Matrix

| Invariant | Enforcement mechanism | Integration coverage | Remaining risk | Operational impact if violated |
|-----------|----------------------|----------------------|----------------|-------------------------------|
| LED-APPEND-ONLY | Code discipline + insert-only persist | Partial (idempotency) | No DB trigger preventing DELETE | Historical truth lost; audits fail |
| LED-SOURCE-ID | UNIQUE + ON CONFLICT DO NOTHING | Yes (`test_inventory_idempotency`) | Manual SQL bypass | Duplicate stock movements |
| LED-IMMUTABLE-QTY | Convention | No dedicated test | Admin scripts | Incorrect balances |
| LED-REPLAY-ORDER | Streaming ORDER BY | Benchmark stream stats | Driver-specific stream quirks | Nondeterministic snapshots |
| LED-REPLAY-DET | Domain pipeline + fingerprints | Yes (unit + benchmark) | Semantics registry drift | Wrong inventory analytics |
| LED-REBUILD-NO-MUTATE | Service boundaries | Implicit | Future refactor mistake | Ledger corruption |
| FIN-DECIMAL | Types + Numeric columns | Unit finance tests | JSON boundaries | Financial rounding errors |
| SNAP-UNIQUE-DAY-SKU-WH | DB UNIQUE + runtime log | Yes (`test_inventory_snapshots`) | Log-only runtime leg | Duplicate snapshot rows / upsert fights |
| SNAP-FP-DET | `snapshot_fingerprint` | Yes (unit) | Field added without FP update | Drift checks false +/- |
| SNAP-DERIVED | Delete window / full delete | Yes | — | Low if rebuild works |
| SNAP-PROMOTE-ATOMIC | Single txn promote | Yes (`test_rebuild_production_guarantees`) | Long txn lock duration | Readers see partial state |
| SNAP-VIS-NO-PARTIAL | MVCC + txn boundary | Yes (concurrent reads test) | READ UNCOMMITTED never used | Flickering stock UI |
| SNAP-INCR-WINDOW | `compute_rebuild_window` | Unit only | Wrong `earliest_affected_date` from API | Stale future snapshots |
| SNAP-FULL-EQ-INCR | Dual code paths | Yes (benchmark + unit) | Carry-forward bugs on edge dates | Incremental ≠ full truth |
| SNAP-PROMOTE-ROW-MATCH | COUNT compare log | Unit only | Log-only | Silent partial promote |
| Q-CLAIM-EXCL | SKIP LOCKED | Yes (`test_queue_lifecycle`) | — | Double ETL processing |
| Q-NO-DUP-PROC | Status filter | Yes | — | Duplicate ledger from same job |
| Q-ACK-TERM | ack() | Yes | Worker crash before ack | Orphan PROCESSING until recover |
| Q-RETRY-BOUND | fail() | Yes | — | Infinite retries / no DLQ |
| Q-VIS-RECOVER | recover_stale | Yes | DLQ leaves `claimed_at` set | Stuck jobs (monitor PROCESSING) |
| Q-IDEMP-ENQUEUE | enqueue dedupe | Yes | Completed job same key blocks re-enqueue via UNIQUE | Stuck uploads |
| Q-BROKER-RLS | QueueSession | Implicit | Misuse of session type | Cross-tenant job access |
| SEM-NO-SILENT-FALLBACK | Explicit errors | Yes (unit) | New version without registry entry | Misclassified operations |
| SEM-INGEST-GATE | assert on process | Yes | — | Deprecated semantics ingested |
| SEM-REBUILD-GATE | assert on replay | Yes | — | Wrong historical classification |
| SEM-FROZEN-ON-ROW | Persist columns | Yes | — | Mixed-version rows in one day |
| SEM-INVALID-NO-INLINE | Queue requirement row | Code review + unit policy tests | Missing background consumer | API latency / lock contention |
| SEM-LIFECYCLE | policy + DB seed | Yes | Cache stale in long-lived workers | Wrong ingest/rebuild allowance |
| OPS-LOCK-FAILFAST | pg_try advisory | Yes | — | Rebuild pile-up / blocking |
| OPS-LOCK-XACT | xact lock | Unit + integration | — | Lock leaks if non-xact lock introduced |
| OPS-ANOMALY-ISOLATED | separate txn | Unit | — | Ledger rollback on anomaly DB error |
| OPS-ANOMALY-BEST-EFFORT | swallow in pipeline | Unit | Silent data quality blind spot | Missing anomaly rows |
| OPS-REBUILD-IDEMP | deterministic recompute | Yes (benchmark) | Floating math if Decimal broken | Flapping fingerprints |
| OPS-DRIFT-READONLY | verification service | Yes (drift E2E) | Operator ignores anomalies | Undetected corruption |
| OPS-CPU-NO-TXN | worker structure | Not integration-tested | Long CPU holds connection | Connection pool exhaustion |
| TEN-RLS | PostgreSQL policies | All integration tests | Migration mistake | Cross-tenant data leak |
| TEN-LOCK-SCOPE | user-derived key | Yes (locking tests) | — | Tenant A blocks Tenant B |
| TEN-ANOMALY-SCOPE | user_id column | Partial | — | Wrong tenant alerts |
| TEN-NO-BYPASS | session classes | Review / migrations only | Accidental bypass in API | Total data exposure |
| TST-ISOLATE-DB | TRUNCATE autouse | All integration | Forgotten autouse on new suite | Flaky tests / false confidence |
| TST-UNIQUE-IDS | convention | Yes | — | Order-dependent failures |
| TST-DET-FIXTURES | fixture modules | Yes | — | Nondeterministic CI |
| TST-REPLAY-EQ | benchmark + unit | Stress-gated benchmark | Not in default CI | Regressions ship unnoticed |
| TST-NO-ORDER | policy | Not automated | — | Order-dependent failures |
| TST-GATE | env vars | Yes | — | CI runs without DB falsely passes |

## Coverage summary

| Layer | Formally documented | DB-enforced | Runtime log probe | Integration test | Unit test only |
|-------|--------------------|-------------|-------------------|------------------|----------------|
| Ledger | Yes | Partial (UNIQUE) | No | Partial | Yes |
| Snapshots | Yes | UNIQUE | Yes | Yes | Yes |
| Queue | Yes | No | No | Yes | Partial |
| Semantics | Yes | Seed table | Yes (draft) | Partial | Yes |
| Operational | Yes | Advisory lock | No | Yes | Partial |
| Multi-tenant | Yes | RLS | No | Implicit | No |
| Testing meta | Yes | — | — | — | — |

## Invariants **not** formally enforced at runtime

These rely on convention, review, or tests only:

- LED-IMMUTABLE-QTY (no DB trigger)
- LED-REBUILD-NO-MUTATE (architectural)
- OPS-CPU-NO-TXN (worker layout)
- SEM-INVALID-NO-INLINE consumer (queue processor may be future work)
- TST-NO-ORDER (process)
- Most **log-only** runtime probes (they detect but do not block)

## Invariants relying **primarily** on integration tests

- SNAP-VIS-NO-PARTIAL / SNAP-PROMOTE-ATOMIC
- Q concurrent claim family
- OPS-DRIFT-READONLY E2E
- TEN-RLS (implicit in all integration tests, no dedicated RLS penetration suite)
- SNAP-FULL-EQ-INCR at scale (`RUN_STRESS_TESTS` benchmark)

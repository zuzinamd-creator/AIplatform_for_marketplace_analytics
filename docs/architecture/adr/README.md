# Architecture Decision Records (ADR)

Index of normative platform decisions. **Status:** Accepted unless marked otherwise.

| ADR | Title | Invariants |
|-----|-------|------------|
| [ADR-001](ADR-001-append-only-ledger.md) | Append-only ledger | LED-* |
| [ADR-002](ADR-002-advisory-locking.md) | Per-tenant advisory locking | OPS-LOCK-* |
| [ADR-003](ADR-003-staging-promote.md) | Staging snapshot promote | SNAP-PROMOTE-*, SNAP-VIS-* |
| [ADR-004](ADR-004-deterministic-rebuild.md) | Deterministic snapshot rebuild | LED-REPLAY-*, SNAP-FP-* |
| [ADR-005](ADR-005-streaming-replay.md) | Streaming ledger replay | LED-REPLAY-ORDER |
| [ADR-006](ADR-006-queue-skip-locked.md) | PostgreSQL SKIP LOCKED queue | Q-* |
| [ADR-007](ADR-007-semantics-governance.md) | Semantics lifecycle governance | SEM-* |
| [ADR-008](ADR-008-anomaly-quarantine.md) | ETL anomaly quarantine | OPS-ANOMALY-* |

When changing code under [ADR-governed paths](../engineering_standards.md#adr-governed-paths), update the relevant ADR or add a new ADR with supersession note.

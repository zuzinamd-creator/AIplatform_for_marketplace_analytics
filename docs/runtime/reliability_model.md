# Reliability model

Enterprise production hardening layer (Phase A) — additive, PostgreSQL-centric.

## Layers

| Layer | Module | Purpose |
|-------|--------|---------|
| Kill switches | `app/runtime/reliability/kill_switches.py` | Worker, orchestrator, AI, maintenance gates |
| Circuit breakers | `app/runtime/reliability/circuit_breaker.py` | Rebuild dispatch + AI provider failure containment |
| Degradation | `app/runtime/reliability/degradation.py` | NORMAL → DEGRADED → LIMITED → MAINTENANCE |
| Containment | `app/runtime/containment/` | Tenant quarantine, DLQ escalation |
| Resilience | `app/runtime/resilience/` | Process heartbeats, orchestrator lease |
| Audit | `app/runtime/audit/operator.py` | Operator/recovery action trail |

## Invariants preserved

Append-only ledgers, advisory locks, staging promote, RLS, deterministic rebuild, governance checks.

## Configuration

See [operational_policies.md](operational_policies.md) and README §2j.

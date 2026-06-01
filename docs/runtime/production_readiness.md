# Production readiness checklist

## Before go-live

- [ ] `alembic upgrade head` (through `0016_production_reliability`)
- [ ] `SECRET_KEY` non-default; `DATABASE_URL` set
- [ ] `DEBUG=false`
- [ ] Single orchestrator replica OR lease-aware deployment
- [ ] `ORCHESTRATOR_ENABLED`, `WORKER_ENABLED`, `AI_ENABLED` reviewed
- [ ] Queue/rebuild thresholds tuned (`RUNTIME_QUEUE_OVERLOAD_THRESHOLD`, etc.)
- [ ] Run validation suite (pytest, ruff, mypy, governance)

## Operational authority

| Action | Authority |
|--------|-----------|
| Kill switches (env) | Platform operator |
| DLQ replay | Tenant operator + audit |
| Semantics promotion | Human approval |
| Maintenance mode | Platform operator |

## Escalation hierarchy

1. Ops APIs (`/ops/runtime/*`)
2. Structured logs + metrics taxonomy
3. `operator_audit_events` / `runtime_autonomy_events`
4. Manual runbooks (`TenantRecoveryService`)

## Maturity target

Phase A: **L3 enterprise reliability** — bounded autonomy, containment, observability, documented degradation.

# Runtime autonomy report (Phase 3)

## Maturity assessment

| Area | Level | Notes |
|------|-------|-------|
| Control plane | L2 | Explicit coordinator, in-process schedules |
| Adaptive dispatch | L2 | Prioritizer + policy throttle + incremental→full |
| Autonomous recovery | L2 | Bounded healer + audit table |
| Health engine | L2 | Multi-dimension scoring + recommendations |
| Scheduling | L2 | Registry + executor; poll-based |
| Ops UX | L2 | `/ops/runtime/*` tenant summaries |

## Operational autonomy limits

- Single-process orchestrator; no Kubernetes-style control plane.
- Autonomy capped per cycle; disabled via `RUNTIME_AUTONOMY_ENABLED`.
- No automatic semantics promotion or ledger mutation outside rebuild pipeline.

## Remaining manual operations

- DLQ replay and poison investigation
- Semantics lifecycle approval
- Capacity scaling (worker/orchestrator replica count)
- Cross-tenant incident response (requires queue_role tooling)

## Catastrophic risks

| Risk | Mitigation |
|------|------------|
| Runaway rebuild dispatch | Per-cycle cap, throttle, runaway metric |
| RLS bypass misuse | Forbidden in runtime; governance check |
| Autonomy storm | Action cap + master switch |
| Lock contention | Defer busy without attempt burn |

## Scale limits

- Fair dispatch O(candidates) per cycle with global listing under `DispatchSession`.
- In-process schedule registry does not coordinate multi-orchestrator (operate one orchestrator or accept duplicate maintenance).
- PostgreSQL advisory locks serialize inventory rebuild per tenant.

## Scheduling model

Poll-driven `ScheduleRegistry` aligned to `ORCHESTRATOR_POLL_INTERVAL_SECONDS`. Maintenance/autonomy intervals = poll × `ORCHESTRATOR_MAINTENANCE_EVERY_CYCLES`.

## Self-healing guarantees

- **Explicit**: every autonomous action logged.
- **Bounded**: max actions per cycle.
- **Reversible**: defer and stale-reset documented as reversible.
- **Tenant-scoped**: mutations via `TenantSession` where applicable.

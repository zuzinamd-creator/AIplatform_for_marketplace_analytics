# Runtime control plane

PostgreSQL-centric operational control for rebuild dispatch, health, scheduling, and bounded autonomy.

## State dimensions

| Dimension | Model | Persistence |
|-----------|--------|-------------|
| Tenant operational | `TenantOperationalState` | Derived each cycle from health + backlog |
| Workload | `WorkloadState` | Derived (idle / throttled / dispatching) |
| Rebuild orchestration | `RebuildOrchestrationStatus` | `snapshot_rebuild_requirements` |
| Runtime health | `RuntimeHealthSeverity` + score | Computed by `RuntimeHealthEvaluator` |
| Scheduling | `ScheduleRegistry` ticks | In-process per orchestrator |

## Coordinator

`RuntimeControlPlane.run_cycle()`:

1. Runs due schedules (maintenance, autonomy, health, queue visibility).
2. Collects global queue + rebuild metrics.
3. Evaluates health and applies overload guards.
4. Optionally dispatches one rebuild via `RebuildDispatcher` (when not throttled).

## Lifecycle

See [runtime_lifecycle.md](runtime_lifecycle.md) for transition tables (`control_plane/lifecycle.py`).

## Ops visibility

Tenant-scoped summaries: `GET /api/v1/ops/runtime/summary`, `GET /api/v1/ops/runtime/health`.

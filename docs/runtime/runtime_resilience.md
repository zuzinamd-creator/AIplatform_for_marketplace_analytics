# Runtime resilience

## Process heartbeats

`ProcessSupervisor` + `ProcessSupervisorRegistry` write to `runtime_process_heartbeats`. Stale rows cleaned after `RELIABILITY_PROCESS_STALE_SECONDS`.

Integrated in ETL worker and orchestrator startup.

## Orchestrator lease

`OrchestratorLeaseService` holds `orchestrator_primary` lease in `runtime_process_leases`. TTL: `RELIABILITY_ORCHESTRATOR_LEASE_TTL_SECONDS`. Only lease holder runs control-plane cycles.

## Graceful shutdown

Workers and orchestrator: SIGINT/SIGTERM → drain flag → release lease → dispose engine.

## Job-level heartbeats

ETL jobs: `last_heartbeat_at` during processing; interval from `WORKER_HEARTBEAT_INTERVAL_SECONDS`.

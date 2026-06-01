# Runtime event taxonomy

Structured metrics via `emit_runtime_metric` / `emit_ai_metric`. Categories in `app/runtime/events/taxonomy.py`.

| Event | Category | When |
|-------|----------|------|
| `runtime_rebuild_trace` | rebuild | Dispatch starts (trace + correlation) |
| `runtime_circuit_opened` | reliability | Breaker opens |
| `runtime_degradation_state` | reliability | Control-plane cycle |
| `runtime_process_heartbeat` | resilience | Supervisor tick |
| `runtime_lease_acquired` | resilience | Orchestrator lease |
| `runtime_tenant_containment` | containment | Quarantine/throttle |
| `operator_audit_action` | operator | Recovery replay, privileged ops |
| `ai_provider_failover` | ai | Primary provider failure |
| `runtime_rebuild_storm_contained` | containment | Hourly rebuild storm |

Correlation IDs: HTTP middleware + worker/orchestrator cycle (`set_correlation_id`). AI runs store `correlation_id` on `ai_execution_runs`.

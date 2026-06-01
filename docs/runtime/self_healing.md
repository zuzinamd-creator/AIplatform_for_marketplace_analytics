# Self-Healing

Phase C extends Phase 3 `AutonomousHealer` via `GovernedRemediationExecutor`:

| Workflow | Mechanism |
|----------|-----------|
| Stale rebuild recovery | `RetrySupervisor` + healer |
| Queue healing | Stuck job recovery sample |
| Tenant defer | Rebuild defer under queue pressure |
| Orchestration self-healing | `ENTERPRISE_OPERATIONS` schedule |
| Degraded recovery | Throttle + forecast-driven decisions |

All actions logged to `runtime_autonomous_actions` and `runtime_autonomy_events`.

Reversible by design; no semantics or ledger writes.

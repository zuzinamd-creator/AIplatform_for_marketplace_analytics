# Autonomous Governance

`AutonomyPermissionMatrix` (`app/runtime/enterprise/governance.py`) enforces safety levels:

| Level | Allowed actions |
|-------|-----------------|
| `off` | None |
| `monitor` | Observe only |
| `limited` | Stale reset, stuck job recovery |
| `standard` | Full decision catalog |

Approval-required: `defer_rebuild`, `throttle_dispatch` (unless dry-run).

Emergency stop: `KillSwitchDomain.AUTONOMY` when `RUNTIME_AUTONOMY_ENABLED=false`.

# Runtime Strategy Layer

`RuntimeStrategyLayer` (`app/runtime/enterprise/strategy.py`) provides adaptive orchestration advice:

| Output | Purpose |
|--------|---------|
| `dispatch_batch_size` | Reduced under overload forecast |
| `throttle_dispatch` | Aligns with `RuntimeOperationalPolicy` |
| `rebuild_schedule_bias` | Fairness when backlog exceeds running |
| `fairness_note` | Operator-readable strategy summary |

Integrates with `AdaptiveRebuildPrioritizer` in the rebuild dispatcher path.

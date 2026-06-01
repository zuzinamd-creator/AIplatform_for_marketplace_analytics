# Operational Forecasting

`RuntimeIntelligenceEngine` (`app/runtime/enterprise/forecasting.py`) — deterministic heuristics:

| Score | Inputs |
|-------|--------|
| Queue saturation | Pending vs overload threshold |
| Rebuild pressure | Pending + deferred vs batch size |
| Overload risk | Weighted combination |
| Autonomy health | Platform health score |
| AI execution pressure | Queue pressure when AI pause enabled |
| Drift score | Failed rebuilds + critical health |

API: `GET /api/v1/ops/runtime/forecast` (tenant-scoped metrics).

Simulation: `POST /api/v1/ops/runtime/simulation` — dry-run full cycle.

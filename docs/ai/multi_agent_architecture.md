# Multi-Agent Architecture

Phase B coordinates specialized advisory agents via `MultiAgentCoordinator` (`app/ai/coordination/coordinator.py`).

## Agent roles

| Role | Responsibility |
|------|----------------|
| Planner | Builds `ActionPlanDTO` with dependency steps |
| Analyst | Runs `AIDecisionEngine` scoring |
| Validator | `validate_recommendation()` — contradictions, stale context |
| Operations Advisor | Notes degraded runtime / rebuild state |
| Coordinator | Assembles final `IntelligenceRunResultDTO` |

## Communication model

Inter-agent messages are `AgentMessageDTO` records (from_role, to_role, message_type, payload_summary). No direct tool invocation between agents; all writes go through `AIIntelligenceEngine` persistence paths.

## Orchestration entrypoint

`AIIntelligenceEngine.run_intelligence()` wraps `AIAnalyticsEngine` + coordinator + governance gate + strategic memory.

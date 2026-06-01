# Agent model

Foundational agent kinds in `app/ai/agents.py`. Each has **bounded autonomy**.

## Agent catalog

| Agent | Responsibility | May persist insight | Escalation |
|-------|----------------|----------------------|------------|
| **analytics** | KPI summaries from DTO | Yes | tenant_analyst |
| **anomaly_investigation** | Explain ETL anomalies + ops context | No | tenant_admin |
| **recommendation** | Suggest actions (advisory) | No | tenant_admin |
| **reporting** | Executive narratives | Yes | tenant_analyst |
| **orchestration_assistant** | Rebuild/queue health explanations | No | platform_operator |

## Allowed tools (per agent)

| Tool | Purpose |
|------|---------|
| `read_analytics_dto` | Load `AIInsightInputDTO` |
| `read_ops_rebuilds` | Rebuild requirement status |
| `read_ops_anomalies` | `etl_anomalies` list |
| `read_ops_queue` | Job queue snapshot |
| `read_semantics_status` | Lifecycle registry |
| `write_ai_insight_draft` | Upsert `ai_insights` (draft) |

## Execution permissions

- `max_tool_calls` — hard cap per run
- `token_budget` — enforced in `ExecutionTrace.assert_within_budget()`
- `may_persist_insight` — gates `AIAction.PERSIST_INSIGHT`

## Escalation paths

When a request exceeds agent scope (e.g. orchestration assistant asked to rebuild):

1. Log `ai_policy_violation` / raise `AIPolicyViolation`
2. Return advisory message pointing to `escalation_path(agent)`
3. Human uses ops playbooks or API — not AI auto-execution

## Adding a new agent

1. Add `AgentKind` value
2. Define `AgentPermissions` in `_AGENT_PERMISSIONS`
3. Register default prompt in `PromptRegistry`
4. Unit tests for policy + permissions
5. Update this doc + [ai_governance.md](ai_governance.md)

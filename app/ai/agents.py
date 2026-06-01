"""Agent kinds, permissions, and escalation paths."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentKind(StrEnum):
    ANALYTICS = "analytics"
    ANALYTICS_ASSISTANT = "analytics_assistant"
    ANOMALY_INVESTIGATION = "anomaly_investigation"
    ANOMALY_INVESTIGATOR = "anomaly_investigator"
    RECOMMENDATION = "recommendation"
    REPORTING = "reporting"
    ORCHESTRATION_ASSISTANT = "orchestration_assistant"
    OPERATIONS_ASSISTANT = "operations_assistant"
    INVENTORY_OPTIMIZER = "inventory_optimizer"
    FORECASTING_ASSISTANT = "forecasting_assistant"


class ToolName(StrEnum):
    """Read-only platform tools AI may invoke through governed adapters."""

    READ_ANALYTICS_DTO = "read_analytics_dto"
    READ_OPS_REBUILDS = "read_ops_rebuilds"
    READ_OPS_ANOMALIES = "read_ops_anomalies"
    READ_OPS_QUEUE = "read_ops_queue"
    READ_SEMANTICS_STATUS = "read_semantics_status"
    WRITE_AI_INSIGHT_DRAFT = "write_ai_insight_draft"


@dataclass(frozen=True)
class AgentPermissions:
    """Bounded autonomy per agent kind."""

    allowed_tools: frozenset[ToolName]
    max_tool_calls: int
    token_budget: int
    may_persist_insight: bool
    requires_human_approval_for: frozenset[str]


_AGENT_PERMISSIONS: dict[AgentKind, AgentPermissions] = {
    AgentKind.ANALYTICS: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_SEMANTICS_STATUS,
                ToolName.WRITE_AI_INSIGHT_DRAFT,
            }
        ),
        max_tool_calls=10,
        token_budget=8000,
        may_persist_insight=True,
        requires_human_approval_for=frozenset({"financial_commitment"}),
    ),
    AgentKind.ANOMALY_INVESTIGATION: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_OPS_ANOMALIES,
                ToolName.READ_OPS_REBUILDS,
                ToolName.READ_OPS_QUEUE,
            }
        ),
        max_tool_calls=15,
        token_budget=12000,
        may_persist_insight=False,
        requires_human_approval_for=frozenset({"remediation_action"}),
    ),
    AgentKind.RECOMMENDATION: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_OPS_REBUILDS,
            }
        ),
        max_tool_calls=8,
        token_budget=6000,
        may_persist_insight=False,
        requires_human_approval_for=frozenset({"pricing_change", "inventory_adjustment"}),
    ),
    AgentKind.REPORTING: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.WRITE_AI_INSIGHT_DRAFT,
            }
        ),
        max_tool_calls=6,
        token_budget=10000,
        may_persist_insight=True,
        requires_human_approval_for=frozenset(),
    ),
    AgentKind.ORCHESTRATION_ASSISTANT: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_OPS_REBUILDS,
                ToolName.READ_OPS_QUEUE,
                ToolName.READ_SEMANTICS_STATUS,
            }
        ),
        max_tool_calls=12,
        token_budget=4000,
        may_persist_insight=False,
        requires_human_approval_for=frozenset({"trigger_rebuild", "replay_dlq"}),
    ),
    AgentKind.ANALYTICS_ASSISTANT: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_SEMANTICS_STATUS,
                ToolName.WRITE_AI_INSIGHT_DRAFT,
            }
        ),
        max_tool_calls=10,
        token_budget=8000,
        may_persist_insight=True,
        requires_human_approval_for=frozenset({"financial_commitment"}),
    ),
    AgentKind.ANOMALY_INVESTIGATOR: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_OPS_ANOMALIES,
                ToolName.READ_OPS_REBUILDS,
            }
        ),
        max_tool_calls=15,
        token_budget=12000,
        may_persist_insight=False,
        requires_human_approval_for=frozenset({"remediation_action"}),
    ),
    AgentKind.OPERATIONS_ASSISTANT: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_OPS_REBUILDS,
                ToolName.READ_OPS_QUEUE,
                ToolName.READ_SEMANTICS_STATUS,
            }
        ),
        max_tool_calls=12,
        token_budget=4000,
        may_persist_insight=False,
        requires_human_approval_for=frozenset({"trigger_rebuild"}),
    ),
    AgentKind.INVENTORY_OPTIMIZER: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_SEMANTICS_STATUS,
                ToolName.WRITE_AI_INSIGHT_DRAFT,
            }
        ),
        max_tool_calls=10,
        token_budget=9000,
        may_persist_insight=True,
        requires_human_approval_for=frozenset({"inventory_adjustment"}),
    ),
    AgentKind.FORECASTING_ASSISTANT: AgentPermissions(
        allowed_tools=frozenset(
            {
                ToolName.READ_ANALYTICS_DTO,
                ToolName.READ_SEMANTICS_STATUS,
            }
        ),
        max_tool_calls=8,
        token_budget=7000,
        may_persist_insight=False,
        requires_human_approval_for=frozenset({"forecast_commit"}),
    ),
}


def permissions_for(agent: AgentKind) -> AgentPermissions:
    return _AGENT_PERMISSIONS[agent]


def escalation_path(agent: AgentKind) -> str:
    """Human operator escalation target for out-of-scope requests."""
    if agent == AgentKind.ORCHESTRATION_ASSISTANT:
        return "platform_operator"
    if agent in (AgentKind.ANOMALY_INVESTIGATION, AgentKind.RECOMMENDATION):
        return "tenant_admin"
    return "tenant_analyst"

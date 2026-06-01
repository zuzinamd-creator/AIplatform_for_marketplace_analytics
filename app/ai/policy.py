"""AI policy enforcement — mutation restrictions and forbidden actions."""

from __future__ import annotations

from enum import StrEnum

from app.ai.agents import AgentKind, ToolName, permissions_for
from app.core.config import settings


class AIAction(StrEnum):
    EXECUTE_AGENT = "execute_agent"
    INVOKE_TOOL = "invoke_tool"
    PERSIST_INSIGHT = "persist_insight"
    MUTATE_LEDGER = "mutate_ledger"
    MUTATE_SNAPSHOT = "mutate_snapshot"
    TRIGGER_REBUILD = "trigger_rebuild"
    ENQUEUE_ETL = "enqueue_etl"
    BYPASS_RLS = "bypass_rls"
    BYPASS_SEMANTICS = "bypass_semantics"


class AIPolicyViolation(Exception):
    """Raised when an AI path attempts a forbidden platform action."""


FORBIDDEN_AI_ACTIONS: frozenset[AIAction] = frozenset(
    {
        AIAction.MUTATE_LEDGER,
        AIAction.MUTATE_SNAPSHOT,
        AIAction.TRIGGER_REBUILD,
        AIAction.ENQUEUE_ETL,
        AIAction.BYPASS_RLS,
        AIAction.BYPASS_SEMANTICS,
    }
)


def assert_ai_action_allowed(
    action: AIAction,
    *,
    agent: AgentKind | None = None,
    tool: ToolName | None = None,
) -> None:
    if action in FORBIDDEN_AI_ACTIONS:
        raise AIPolicyViolation(f"AI forbidden action: {action.value}")

    if action == AIAction.PERSIST_INSIGHT:
        if agent is None:
            raise AIPolicyViolation("persist_insight requires agent context")
        if not permissions_for(agent).may_persist_insight:
            raise AIPolicyViolation(f"agent {agent.value} may not persist insights")

    if action == AIAction.INVOKE_TOOL:
        if agent is None or tool is None:
            raise AIPolicyViolation("invoke_tool requires agent and tool")
        perms = permissions_for(agent)
        if tool not in perms.allowed_tools:
            raise AIPolicyViolation(f"tool {tool.value} not allowed for {agent.value}")


def assert_agent_enabled(agent: AgentKind) -> None:
    disabled = {s.strip() for s in settings.ai_disabled_agents.split(",") if s.strip()}
    if agent.value in disabled:
        raise AIPolicyViolation(f"agent {agent.value} disabled by configuration")

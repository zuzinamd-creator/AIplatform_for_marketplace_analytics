"""Unit tests for AI policy, prompts, and safety budgets."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.ai.agents import AgentKind, ToolName, permissions_for
from app.ai.policy import AIAction, AIPolicyViolation, assert_ai_action_allowed
from app.ai.prompts import PromptRegistry
from app.ai.safety import ExecutionTrace
from app.dto.analytics_dto import AIInsightInputDTO, ContextDTO, MetricsDTO


def test_forbidden_mutate_ledger() -> None:
    with pytest.raises(AIPolicyViolation):
        assert_ai_action_allowed(AIAction.MUTATE_LEDGER)


def test_analytics_agent_may_persist() -> None:
    assert_ai_action_allowed(
        AIAction.PERSIST_INSIGHT,
        agent=AgentKind.ANALYTICS,
    )


def test_anomaly_agent_may_not_persist() -> None:
    with pytest.raises(AIPolicyViolation):
        assert_ai_action_allowed(
            AIAction.PERSIST_INSIGHT,
            agent=AgentKind.ANOMALY_INVESTIGATION,
        )


def test_tool_not_allowed_for_agent() -> None:
    with pytest.raises(AIPolicyViolation):
        assert_ai_action_allowed(
            AIAction.INVOKE_TOOL,
            agent=AgentKind.REPORTING,
            tool=ToolName.READ_OPS_QUEUE,
        )


def test_prompt_registry_known_id() -> None:
    contract = PromptRegistry.get("analytics.summary.v1")
    assert contract.version == "1.0.0"
    assert "narrative_summary" in contract.probabilistic_sections


def test_execution_trace_tool_budget() -> None:
    trace = ExecutionTrace(
        run_id=uuid4(),
        agent=AgentKind.ORCHESTRATION_ASSISTANT,
        prompt_id="x",
        prompt_version="1.0.0",
    )
    perms = permissions_for(AgentKind.ORCHESTRATION_ASSISTANT)
    for _ in range(perms.max_tool_calls + 1):
        trace.record_tool_call(ToolName.READ_OPS_QUEUE, status="ok")
    with pytest.raises(AIPolicyViolation):
        trace.assert_within_budget()


def test_insight_dto_strict() -> None:
    dto = AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date(2026, 1, 1),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(sku_count=1, total_revenue=Decimal("100")),
    )
    legacy = dto.to_legacy_dict()
    assert legacy["sku_count"] == 1

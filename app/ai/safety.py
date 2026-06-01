"""Execution safety: budgets, timeouts, tracing, failure isolation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from app.ai.agents import AgentKind, ToolName, permissions_for
from app.ai.metrics import emit_ai_metric
from app.ai.policy import AIAction, AIPolicyViolation, assert_ai_action_allowed
from app.core.config import settings


@dataclass
class ExecutionTrace:
    run_id: UUID
    agent: AgentKind
    prompt_id: str
    prompt_version: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tool_calls: list[dict[str, str]] = field(default_factory=list)
    runtime_events: list[dict] = field(default_factory=list)
    tokens_used: int = 0
    _started_perf: float = field(default_factory=perf_counter, repr=False)

    def record_tool_call(self, tool: ToolName, *, status: str, detail: str = "") -> None:
        self.tool_calls.append(
            {
                "tool": tool.value,
                "status": status,
                "detail": detail[:512],
                "at": datetime.now(UTC).isoformat(),
            }
        )
        emit_ai_metric(
            "ai_tool_call",
            run_id=str(self.run_id),
            tool=tool.value,
            status=status,
            agent=self.agent.value,
        )

    def add_tokens(self, count: int) -> None:
        self.tokens_used += count

    def elapsed_ms(self) -> float:
        return round((perf_counter() - self._started_perf) * 1000, 2)

    def assert_within_budget(self) -> None:
        perms = permissions_for(self.agent)
        if self.tokens_used > perms.token_budget:
            raise AIPolicyViolation(
                f"token budget exceeded: {self.tokens_used} > {perms.token_budget}"
            )
        if len(self.tool_calls) > perms.max_tool_calls:
            raise AIPolicyViolation(
                f"tool call budget exceeded: {len(self.tool_calls)} > {perms.max_tool_calls}"
            )
        if self.elapsed_ms() > settings.ai_execution_timeout_seconds * 1000:
            raise AIPolicyViolation(
                f"execution timeout exceeded: {self.elapsed_ms()}ms"
            )

    def record_runtime_event(self, event_type: str, **fields: str) -> None:
        payload: dict[str, str] = {"event": event_type, "at": datetime.now(UTC).isoformat()}
        for k, v in fields.items():
            payload[k] = str(v)[:512]
        self.runtime_events.append(payload)

    def audit_payload(self) -> list:
        return list(self.tool_calls) + list(self.runtime_events)


class ExecutionSafetyEnforcer:
    """Pre-flight checks before tool invocation."""

    @staticmethod
    def validate_tool_invocation(
        trace: ExecutionTrace,
        tool: ToolName,
    ) -> None:
        assert_ai_action_allowed(AIAction.INVOKE_TOOL, agent=trace.agent, tool=tool)
        trace.record_tool_call(tool, status="invoked")

    @staticmethod
    def validate_persist(trace: ExecutionTrace) -> None:
        assert_ai_action_allowed(AIAction.PERSIST_INSIGHT, agent=trace.agent)

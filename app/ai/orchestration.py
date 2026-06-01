"""AI orchestration service — lifecycle, audit persistence, no autonomous mutations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents import AgentKind, ToolName, permissions_for
from app.ai.context import AIContextAssembler, AIExecutionContext
from app.ai.metrics import emit_ai_metric
from app.ai.policy import AIAction, AIPolicyViolation, assert_ai_action_allowed
from app.ai.prompts import get_prompt_contract
from app.ai.safety import ExecutionSafetyEnforcer, ExecutionTrace
from app.core.config import settings
from app.core.observability.context import get_correlation_id
from app.core.security_context import TenantSession
from app.dto.analytics_dto import AIInsightInputDTO
from app.models.ai_execution import AIExecutionRun, AIExecutionStatus


class AIOrchestrationService:
    """
    Governed entrypoint for AI runs.

    Does not call external LLMs — prepares context, enforces policy, persists audit rows.
    Future LLM adapters plug in behind this service.
    """

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def begin_run(
        self,
        *,
        agent: AgentKind,
        prompt_id: str,
        insight_input: AIInsightInputDTO | None = None,
        semantics_version: str = "1.0",
    ) -> tuple[AIExecutionRun, AIExecutionContext, ExecutionTrace]:
        if not settings.ai_enabled:
            raise AIPolicyViolation("AI layer disabled (AI_ENABLED=false)")

        assert_ai_action_allowed(AIAction.EXECUTE_AGENT, agent=agent)
        contract = get_prompt_contract(prompt_id)
        perms = permissions_for(agent)

        ctx = await AIContextAssembler(self.db, self.user_id).assemble(
            semantics_version=semantics_version,
            insight_input=insight_input,
        )
        if insight_input is not None and not ctx.context_valid:
            raise AIPolicyViolation(ctx.invalid_reason or "invalid AI context")

        run_id = uuid4()
        trace = ExecutionTrace(
            run_id=run_id,
            agent=agent,
            prompt_id=contract.prompt_id,
            prompt_version=contract.version,
        )

        status = AIExecutionStatus.DEGRADED if ctx.degraded_mode else AIExecutionStatus.RUNNING
        run = AIExecutionRun(
            id=run_id,
            user_id=self.user_id,
            agent_kind=agent.value,
            status=status,
            prompt_id=contract.prompt_id,
            prompt_version=contract.version,
            correlation_id=get_correlation_id(),
            semantics_version=semantics_version,
            context_valid=ctx.context_valid,
            degraded_mode=ctx.degraded_mode,
            token_budget=perms.token_budget,
            tokens_used=0,
            tool_call_count=0,
            started_at=datetime.now(UTC),
            audit_events=[],
        )

        async with TenantSession.transaction(self.db, self.user_id):
            self.db.add(run)
            await self.db.flush()

        emit_ai_metric(
            "ai_run_started",
            run_id=str(run_id),
            user_id=str(self.user_id),
            agent=agent.value,
            prompt_id=prompt_id,
            degraded_mode=ctx.degraded_mode,
        )
        return run, ctx, trace

    async def complete_run(
        self,
        run: AIExecutionRun,
        trace: ExecutionTrace,
        *,
        output_insight_id: UUID | None = None,
        tokens_used: int = 0,
        provider_name: str | None = None,
        model_name: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        estimated_cost: float | None = None,
        runtime_metadata: dict | None = None,
    ) -> AIExecutionRun:
        trace.add_tokens(tokens_used)
        trace.assert_within_budget()

        async with TenantSession.transaction(self.db, self.user_id):
            row = await self.db.get(AIExecutionRun, run.id)
            if row is None:
                raise AIPolicyViolation(f"run {run.id} not found")
            row.status = (
                AIExecutionStatus.DEGRADED if row.degraded_mode else AIExecutionStatus.SUCCEEDED
            )
            row.tokens_used = trace.tokens_used
            row.provider_name = provider_name
            row.model_name = model_name
            row.prompt_tokens = prompt_tokens
            row.completion_tokens = completion_tokens
            row.estimated_cost = estimated_cost
            row.tool_call_count = len(trace.tool_calls)
            row.duration_ms = int(trace.elapsed_ms())
            row.audit_events = trace.audit_payload()
            row.runtime_metadata = runtime_metadata
            row.output_insight_id = output_insight_id
            row.completed_at = datetime.now(UTC)

        emit_ai_metric(
            "ai_run_completed",
            run_id=str(run.id),
            user_id=str(self.user_id),
            duration_ms=int(trace.elapsed_ms()),
            tokens_used=trace.tokens_used,
        )
        return row

    async def fail_run(
        self,
        run: AIExecutionRun,
        trace: ExecutionTrace,
        *,
        error: str,
    ) -> AIExecutionRun:
        async with TenantSession.transaction(self.db, self.user_id):
            row = await self.db.get(AIExecutionRun, run.id)
            if row is None:
                raise AIPolicyViolation(f"run {run.id} not found")
            row.status = AIExecutionStatus.FAILED
            row.last_error = error[:4000]
            row.tokens_used = trace.tokens_used
            row.tool_call_count = len(trace.tool_calls)
            row.duration_ms = int(trace.elapsed_ms())
            row.audit_events = trace.audit_payload()
            row.completed_at = datetime.now(UTC)

        emit_ai_metric(
            "ai_run_failed",
            run_id=str(run.id),
            user_id=str(self.user_id),
            error=error[:500],
        )
        return row

    def invoke_tool(self, trace: ExecutionTrace, tool: ToolName) -> None:
        """Record governed tool invocation (adapter executes separately)."""
        ExecutionSafetyEnforcer.validate_tool_invocation(trace, tool)

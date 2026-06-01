"""AI analytics engine — governed workflows with provider adapters."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents import ToolName
from app.ai.analytics.workflows import spec_for
from app.ai.grounding import build_grounded_context
from app.ai.memory import AISessionMemory, new_session_id
from app.ai.metrics import emit_ai_metric
from app.ai.orchestration import AIOrchestrationService
from app.ai.policy import AIPolicyViolation, assert_agent_enabled
from app.ai.prompts.runtime import render_prompt
from app.ai.prompts.v3.registry import PromptRegistryV3
from app.ai.providers.cost_governance import assert_daily_cost_allowed, assert_run_cost_allowed
from app.ai.providers.factory import get_llm_resolution
from app.ai.providers.failover import mark_provider_failure, mark_provider_success
from app.ai.providers.pricing import estimate_cost_usd
from app.ai.providers.response_cache import cache_key as llm_cache_key
from app.ai.providers.response_cache import get as cache_get
from app.ai.providers.response_cache import set as cache_set
from app.ai.providers.retry import with_provider_retry
from app.ai.providers.types import LLMMessage, LLMRequest
from app.ai.rate_limit import check_tenant_rate_limit
from app.ai.safety import ExecutionTrace
from app.ai.validation import validate_insight_output
from app.core.config import settings
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, ValidatedInsightDTO
from app.dto.analytics_dto import AIInsightInputDTO
from app.models.ai_execution import AIExecutionRun
from app.models.ai_insights import AIInsight, InsightStatus
from app.runtime.observability import collect_global_queue_metrics


class AIAnalyticsEngine:
    """Production analytics entrypoint (advisory-only, fully audited)."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self._orchestration = AIOrchestrationService(db, user_id)

    async def execute(
        self,
        request: AIRunRequestDTO,
        *,
        insight_input: AIInsightInputDTO | None = None,
    ) -> tuple[AIExecutionRun, ValidatedInsightDTO, UUID | None]:
        await _assert_ai_runtime_allowed(self.user_id)
        check_tenant_rate_limit(self.user_id)
        wf_spec = spec_for(request.workflow)
        if request.prompt_id != wf_spec.prompt_id:
            raise AIPolicyViolation("prompt_id does not match workflow specification")
        assert_agent_enabled(wf_spec.agent)

        session_id = request.session_id or new_session_id()
        run, ctx, trace = await self._orchestration.begin_run(
            agent=wf_spec.agent,
            prompt_id=wf_spec.prompt_id,
            insight_input=insight_input,
            semantics_version=request.semantics_version,
        )
        grounded = build_grounded_context(ctx)
        memory = AISessionMemory(self.db, self.user_id)
        history = await memory.load_recent(session_id)

        self._orchestration.invoke_tool(trace, ToolName.READ_ANALYTICS_DTO)
        await assert_daily_cost_allowed(self.db, self.user_id)
        resolution, model_role, model_name = get_llm_resolution(
            workflow=request.workflow.value, streaming=False
        )
        llm = resolution.adapter
        rendered = render_prompt(grounded=grounded, workflow=request.workflow.value)
        v3_contract = None
        if settings.ai_prompt_runtime_version == "v3":
            v3_contract = PromptRegistryV3.resolve_for_workflow(request.workflow.value)
            trace.prompt_version = v3_contract.version
        trace.record_runtime_event(
            "prompt_rendered",
            template_id=rendered.template_id,
            template_version=rendered.template_version,
            runtime=settings.ai_prompt_runtime_version,
        )
        messages = [LLMMessage(role="system", content=rendered.system)]
        for role, content in history:
            messages.append(LLMMessage(role=role, content=content))
        messages.append(LLMMessage(role="user", content=rendered.user))

        ck = llm_cache_key(system=rendered.system, user=rendered.user, model=model_name)
        cached_body = cache_get(ck)
        runtime_meta = {
            "provider_id": resolution.provider_id,
            "model": model_name,
            "model_role": model_role.value,
            "used_failover": resolution.used_failover,
            "degraded_to_mock": resolution.degraded_to_mock,
            "prompt_runtime": settings.ai_prompt_runtime_version,
            "prompt_template_id": rendered.template_id,
            "v3_prompt_id": v3_contract.prompt_id if v3_contract else None,
            "cache_hit": bool(cached_body),
        }
        trace.record_runtime_event(
            "provider_resolved",
            provider=resolution.provider_id,
            failover=str(resolution.used_failover),
            degraded=str(resolution.degraded_to_mock),
        )

        try:
            if cached_body:
                response_content = cached_body
                prompt_t, completion_t = 0, 0
                provider_label = resolution.provider_id
                model_used = model_name
            else:
                response = await with_provider_retry(
                    lambda: llm.complete(
                        LLMRequest(
                            model=model_name,
                            messages=tuple(messages),
                            max_tokens=min(2048, settings.ai_default_token_budget),
                            metadata={
                                "prompt_id": wf_spec.prompt_id,
                                "workflow": request.workflow.value,
                                "run_id": str(run.id),
                            },
                        )
                    ),
                    operation_name="llm.complete",
                )
                response_content = response.content
                prompt_t = response.prompt_tokens
                completion_t = response.completion_tokens
                provider_label = response.provider
                model_used = response.model
                cache_set(ck, response_content)
                mark_provider_success(resolution.provider_id)

            trace.add_tokens(prompt_t + completion_t)
            estimated_cost = estimate_cost_usd(
                model=model_used,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
            )
            assert_run_cost_allowed(estimated_cost)
            validated = validate_insight_output(
                workflow=request.workflow,
                grounded=grounded,
                raw_output=response_content,
            )
            insight_id = await self._persist_advisory_insight(
                validated,
                trace=trace,
                run=run,
                report_id=request.report_id,
            )
            await memory.append_turn(
                session_id=session_id,
                role="assistant",
                content=validated.summary,
                run_id=run.id,
            )
            if insight_id is not None:
                self._orchestration.invoke_tool(trace, ToolName.WRITE_AI_INSIGHT_DRAFT)
            await self._orchestration.complete_run(
                run,
                trace,
                output_insight_id=insight_id,
                tokens_used=trace.tokens_used,
                provider_name=provider_label,
                model_name=model_used,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
                estimated_cost=estimated_cost,
                runtime_metadata=runtime_meta,
            )
            emit_ai_metric(
                "ai_insight_generated",
                run_id=str(run.id),
                workflow=request.workflow.value,
                confidence=str(validated.confidence),
                provider=provider_label,
            )
            return run, validated, insight_id
        except Exception as exc:
            mark_provider_failure(resolution.provider_id, str(exc))
            await self._orchestration.fail_run(run, trace, error=str(exc))
            raise

    async def execute_stream(
        self,
        request: AIRunRequestDTO,
        *,
        insight_input: AIInsightInputDTO | None = None,
    ):
        """Streaming version of execute().

        Yields dict events:
        - {"type": "delta", "text": "..."}
        - {"type": "final", "run_id": "...", "insight_id": "...", "summary": "..."}
        """
        await _assert_ai_runtime_allowed(self.user_id)
        check_tenant_rate_limit(self.user_id)
        wf_spec = spec_for(request.workflow)
        if request.prompt_id != wf_spec.prompt_id:
            raise AIPolicyViolation("prompt_id does not match workflow specification")
        assert_agent_enabled(wf_spec.agent)

        session_id = request.session_id or new_session_id()
        run, ctx, trace = await self._orchestration.begin_run(
            agent=wf_spec.agent,
            prompt_id=wf_spec.prompt_id,
            insight_input=insight_input,
            semantics_version=request.semantics_version,
        )
        grounded = build_grounded_context(ctx)
        memory = AISessionMemory(self.db, self.user_id)
        history = await memory.load_recent(session_id)

        if not settings.ai_enable_streaming:
            raise AIPolicyViolation("streaming disabled (AI_ENABLE_STREAMING=false)")

        self._orchestration.invoke_tool(trace, ToolName.READ_ANALYTICS_DTO)
        await assert_daily_cost_allowed(self.db, self.user_id)
        resolution, model_role, model_name = get_llm_resolution(
            workflow=request.workflow.value, streaming=True
        )
        llm = resolution.adapter
        rendered = render_prompt(grounded=grounded, workflow=request.workflow.value)
        messages = [LLMMessage(role="system", content=rendered.system)]
        for role, content in history:
            messages.append(LLMMessage(role=role, content=content))
        messages.append(LLMMessage(role="user", content=rendered.user))

        req = LLMRequest(
            model=model_name,
            messages=tuple(messages),
            max_tokens=min(2048, settings.ai_default_token_budget),
            metadata={
                "prompt_id": wf_spec.prompt_id,
                "workflow": request.workflow.value,
                "run_id": str(run.id),
                "model_role": model_role.value,
            },
        )
        runtime_meta = {
            "provider_id": resolution.provider_id,
            "model": model_name,
            "model_role": model_role.value,
            "streaming": True,
            "used_failover": resolution.used_failover,
            "degraded_to_mock": resolution.degraded_to_mock,
        }

        content_accum = ""
        prompt_t = 0
        completion_t = 0
        try:
            if hasattr(llm, "stream"):
                async for evt in llm.stream(req):  # type: ignore[attr-defined]
                    delta = getattr(evt, "delta", "") if not isinstance(evt, dict) else str(evt.get("delta", ""))
                    if getattr(evt, "prompt_tokens", None) is not None:
                        prompt_t = int(evt.prompt_tokens)  # type: ignore[attr-defined]
                    if getattr(evt, "completion_tokens", None) is not None:
                        completion_t = int(evt.completion_tokens)  # type: ignore[attr-defined]
                    if delta:
                        content_accum += delta
                        yield {"type": "delta", "text": delta}
            else:
                r = await llm.complete(req)
                prompt_t = r.prompt_tokens
                completion_t = r.completion_tokens
                content_accum = r.content
                yield {"type": "delta", "text": r.content}

            trace.add_tokens(prompt_t + completion_t)
            estimated_cost = estimate_cost_usd(
                model=req.model,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
            )
            validated = validate_insight_output(
                workflow=request.workflow,
                grounded=grounded,
                raw_output=content_accum,
            )
            insight_id = await self._persist_advisory_insight(
                validated,
                trace=trace,
                run=run,
                report_id=request.report_id,
            )
            await memory.append_turn(
                session_id=session_id,
                role="assistant",
                content=validated.summary,
                run_id=run.id,
            )
            if insight_id is not None:
                self._orchestration.invoke_tool(trace, ToolName.WRITE_AI_INSIGHT_DRAFT)
            assert_run_cost_allowed(estimated_cost)
            mark_provider_success(resolution.provider_id)
            await self._orchestration.complete_run(
                run,
                trace,
                output_insight_id=insight_id,
                tokens_used=trace.tokens_used,
                provider_name=getattr(llm, "provider_name", "unknown"),
                model_name=req.model,
                prompt_tokens=prompt_t,
                completion_tokens=completion_t,
                estimated_cost=estimated_cost,
                runtime_metadata=runtime_meta,
            )
            yield {
                "type": "final",
                "run_id": str(run.id),
                "insight_id": str(insight_id) if insight_id else None,
                "confidence": str(validated.confidence),
                "summary": validated.summary,
            }
        except Exception as exc:
            mark_provider_failure(resolution.provider_id, str(exc))
            await self._orchestration.fail_run(run, trace, error=str(exc))
            raise

    async def _persist_advisory_insight(
        self,
        validated: ValidatedInsightDTO,
        *,
        trace: ExecutionTrace,
        run: AIExecutionRun,
        report_id: UUID | None,
    ) -> UUID | None:
        from app.ai.agents import permissions_for

        if not permissions_for(trace.agent).may_persist_insight:
            return None

        payload = {
            "workflow": validated.workflow.value,
            "semantics_version": validated.semantics_version,
            "confidence": str(validated.confidence),
            "degraded_mode": validated.degraded_mode,
            "stale_data_warning": validated.stale_data_warning,
            "bullets": validated.bullets,
            "unsupported_claims": validated.unsupported_claims,
            "advisory_only": True,
        }
        if report_id is not None:
            payload["report_id"] = str(report_id)

        insight = AIInsight(
            user_id=self.user_id,
            insight_type=validated.workflow.value,
            status=InsightStatus.READY,
            title=validated.title,
            summary=validated.summary,
            context_payload=payload,
            confidence_score=float(validated.confidence),
            workflow_type=validated.workflow.value,
            advisory_metadata={
                "evidence_complete": validated.evidence_complete,
                "run_id": str(run.id),
            },
        )
        async with TenantSession.transaction(self.db, self.user_id):
            self.db.add(insight)
            await self.db.flush()
            return insight.id


async def _assert_ai_runtime_allowed(user_id: UUID) -> None:
    from app.core.database import SessionLocal
    from app.runtime.containment.tenant_guard import TenantContainmentGuard
    from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches

    switch = RuntimeKillSwitches.check(KillSwitchDomain.AI_EXECUTION)
    if not switch.allowed:
        raise AIPolicyViolation(switch.reason)
    async with SessionLocal() as db:
        queue = await collect_global_queue_metrics(db)
    if RuntimeKillSwitches.ai_paused_for_overload(queue_pending=queue.pending_count):
        raise AIPolicyViolation("AI paused while platform queue overloaded")
    async with SessionLocal() as db:
        guard = await TenantContainmentGuard(db).check(user_id)
    if not guard.allowed:
        raise AIPolicyViolation(f"tenant contained: {guard.reason}")


def _build_system_prompt(grounded, workflow: str) -> str:
    return (
        "You are an advisory analytics assistant. "
        "Never mutate ledgers or claim authoritative financial truth. "
        f"Semantics version: {grounded.semantics_version}. "
        f"Data as-of: {grounded.data_as_of.isoformat()}. "
        f"Source period: {grounded.source_period_start} .. {grounded.source_period_end}. "
        f"Freshness: {grounded.freshness_note}. "
        f"Degraded mode: {grounded.degraded_mode}. "
        f"Workflow: {workflow}. "
        "Respond in JSON with keys: summary, bullets, confidence_hint."
    )

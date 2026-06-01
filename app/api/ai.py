"""Governed AI analytics API (JWT + RLS)."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.dto.ai_analytics_dto import AIRunRequestDTO
from app.models.report import Marketplace
from app.models.user import User
from app.schemas.ai import (
    AIExecutionResultResponse,
    AIInsightResponse,
    AIRunCreateRequest,
    AIRunDetailResponse,
    AIRunResponse,
    PaginatedAIInsightsResponse,
    PaginatedAIRunsResponse,
)
from app.schemas.ai_costs import AICostsResponse, AIProviderStatusResponse
from app.schemas.ai_intelligence import (
    AIDigestResponse,
    AIOperationalStatusResponse,
    ConversationReplyResponse,
    DigestSectionResponse,
    ExplainabilityResponse,
    IntelligenceRunCreateRequest,
    IntelligenceRunResponse,
    PaginatedRecommendationsResponse,
    PeriodIntelligenceRunCreateRequest,
    PriorityQueueItemResponse,
    RecommendationAskRequest,
    RecommendationFeedbackRequest,
    RecommendationResponse,
    RecommendationStatsResponse,
    RecommendationWorkflowRequest,
    TodaysFocusResponse,
    UsefulnessMetricsResponse,
)
from app.schemas.ai_usage import AIUsageResponse
from app.services.ai_service import AIService

router = APIRouter()


@router.post("/runs", response_model=AIExecutionResultResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_run(
    body: AIRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIExecutionResultResponse:
    svc = AIService(db, current_user.id)
    try:
        run, validated, insight_id = await svc.create_run(
            AIRunRequestDTO(
                workflow=body.workflow,
                prompt_id=body.prompt_id,
                semantics_version=body.semantics_version,
                session_id=body.session_id,
                report_id=body.report_id,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    row = await svc.get_run(run.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="run missing")
    return AIExecutionResultResponse(
        run=AIRunDetailResponse.model_validate(row),
        insight_id=insight_id,
        confidence=validated.confidence,
        degraded_mode=validated.degraded_mode,
        stale_data_warning=validated.stale_data_warning,
        summary=validated.summary,
    )


@router.post("/runs/stream", status_code=status.HTTP_200_OK)
async def create_ai_run_stream(
    body: AIRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AIService(db, current_user.id)

    async def event_stream():
        try:
            async for evt in svc.create_run_stream(
                AIRunRequestDTO(
                    workflow=body.workflow,
                    prompt_id=body.prompt_id,
                    semantics_version=body.semantics_version,
                    session_id=body.session_id,
                    report_id=body.report_id,
                )
            ):
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)[:500]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs", response_model=PaginatedAIRunsResponse)
async def list_ai_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAIRunsResponse:
    svc = AIService(db, current_user.id)
    rows, total = await svc.list_runs(skip=skip, limit=limit)
    return PaginatedAIRunsResponse(
        items=[AIRunResponse.model_validate(r) for r in rows],
        page=svc.page_meta(total, skip, limit),
    )


@router.get("/runs/{run_id}", response_model=AIRunDetailResponse)
async def get_ai_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIRunDetailResponse:
    row = await AIService(db, current_user.id).get_run(run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return AIRunDetailResponse.model_validate(row)


@router.get("/executions/{run_id}", response_model=AIRunDetailResponse)
async def get_ai_execution(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIRunDetailResponse:
    return await get_ai_run(run_id, db, current_user)


@router.get("/insights", response_model=PaginatedAIInsightsResponse)
async def list_ai_insights(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    workflow: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAIInsightsResponse:
    svc = AIService(db, current_user.id)
    rows, total = await svc.list_insights(skip=skip, limit=limit, workflow=workflow)
    return PaginatedAIInsightsResponse(
        items=[AIInsightResponse.model_validate(r) for r in rows],
        page=svc.page_meta(total, skip, limit),
    )


@router.get("/insights/{insight_id}", response_model=AIInsightResponse)
async def get_ai_insight(
    insight_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIInsightResponse:
    row = await AIService(db, current_user.id).get_insight(insight_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="insight not found")
    return AIInsightResponse.model_validate(row)


@router.post(
    "/intelligence/runs",
    response_model=IntelligenceRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_intelligence_run(
    body: IntelligenceRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntelligenceRunResponse:
    svc = AIService(db, current_user.id)
    try:
        result = await svc.run_intelligence(
            AIRunRequestDTO(
                workflow=body.workflow,
                prompt_id=body.prompt_id,
                semantics_version=body.semantics_version,
                session_id=body.session_id,
                report_id=body.report_id,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    rec_row = None
    if result.recommendation_id is not None:
        rec_row = await svc.get_recommendation(result.recommendation_id)

    explain = None
    if result.explainability is not None:
        explain = ExplainabilityResponse(
            summary_for_operator=result.explainability.summary_for_operator,
            confidence_rationale=result.explainability.confidence_rationale,
            evidence_graph=result.explainability.evidence_graph.model_dump(mode="json"),
            reasoning_trace={
                "steps": [s.model_dump(mode="json") for s in result.explainability.reasoning_trace],
            },
            provenance=result.explainability.provenance,
            freshness_score=result.explainability.freshness_score,
        )

    return IntelligenceRunResponse(
        run_id=result.run_id,
        insight_id=result.insight_id,
        recommendation_id=result.recommendation_id,
        recommendation=RecommendationResponse.model_validate(rec_row) if rec_row else None,
        explainability=explain,
        confidence=result.recommendation.confidence,
        requires_human_approval=result.recommendation.requires_human_approval,
        summary=result.recommendation.summary,
    )


@router.post(
    "/intelligence/period-runs",
    response_model=IntelligenceRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_intelligence_run_for_period(
    body: PeriodIntelligenceRunCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntelligenceRunResponse:
    svc = AIService(db, current_user.id)
    try:
        result = await svc.run_intelligence_for_period(
            AIRunRequestDTO(
                workflow=body.workflow,
                prompt_id=body.prompt_id,
                semantics_version=body.semantics_version,
                session_id=body.session_id,
                report_id=None,
            ),
            marketplace=Marketplace(body.marketplace.lower()),
            period_start=body.period_start,
            period_end=body.period_end,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    rec_row = None
    if result.recommendation_id is not None:
        rec_row = await svc.get_recommendation(result.recommendation_id)

    explain = None
    if result.explainability is not None:
        explain = ExplainabilityResponse(
            summary_for_operator=result.explainability.summary_for_operator,
            confidence_rationale=result.explainability.confidence_rationale,
            evidence_graph=result.explainability.evidence_graph.model_dump(mode="json"),
            reasoning_trace={
                "steps": [s.model_dump(mode="json") for s in result.explainability.reasoning_trace],
            },
            provenance=result.explainability.provenance,
            freshness_score=result.explainability.freshness_score,
        )

    return IntelligenceRunResponse(
        run_id=result.run_id,
        insight_id=result.insight_id,
        recommendation_id=result.recommendation_id,
        recommendation=RecommendationResponse.model_validate(rec_row) if rec_row else None,
        explainability=explain,
        confidence=result.recommendation.confidence,
        requires_human_approval=result.recommendation.requires_human_approval,
        summary=result.recommendation.summary,
    )


@router.get("/recommendations", response_model=PaginatedRecommendationsResponse)
async def list_recommendations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    seller_state: str | None = None,
    group: str | None = Query(None, description="inbox = active + saved"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedRecommendationsResponse:
    svc = AIService(db, current_user.id)
    rows, total = await svc.list_recommendations(
        skip=skip, limit=limit, seller_state=seller_state, group=group
    )
    return PaginatedRecommendationsResponse(
        items=[RecommendationResponse.model_validate(r) for r in rows],
        page=svc.page_meta(total, skip, limit),
    )


@router.get("/recommendations/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    row = await AIService(db, current_user.id).get_recommendation(recommendation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recommendation not found")
    return RecommendationResponse.model_validate(row)


@router.get("/recommendations/stats", response_model=RecommendationStatsResponse)
async def get_recommendation_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationStatsResponse:
    return await AIService(db, current_user.id).recommendation_stats()


@router.get(
    "/recommendations/{recommendation_id}/explainability",
    response_model=ExplainabilityResponse,
)
async def get_recommendation_explainability(
    recommendation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExplainabilityResponse:
    row = await AIService(db, current_user.id).get_recommendation(recommendation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recommendation not found")
    graph = row.evidence_graph or {"nodes": [], "edges": []}
    trace = row.reasoning_trace or {"steps": []}
    if "domain_insights" not in trace and isinstance(trace.get("multi_layer"), dict):
        ml = trace["multi_layer"]
        if isinstance(ml.get("domain_insights"), list):
            trace = {**trace, "domain_insights": ml["domain_insights"]}
    plan = row.action_plan or {}
    usefulness = plan.get("seller_usefulness") or {}
    trust_context = {
        "confidence_explanation": usefulness.get("confidence_explanation"),
        "limitations": usefulness.get("limitations", []),
        "urgency": usefulness.get("urgency"),
        "stale_data_note": (
            "Verify KPI freshness in analytics before acting."
            if usefulness.get("limitations")
            and any("stale" in str(x).lower() for x in usefulness.get("limitations", []))
            else None
        ),
        "advisory_only": True,
        "seller_workflow_state": row.seller_workflow_state,
    }
    rationale = str(
        usefulness.get("confidence_explanation")
        or f"Stored confidence {row.confidence_score}; risk {row.risk_class.value}"
    )
    return ExplainabilityResponse(
        summary_for_operator=row.summary[:500],
        confidence_rationale=rationale[:2000],
        evidence_graph=graph,
        reasoning_trace=trace,
        provenance={
            "run_id": str(row.run_id) if row.run_id else "",
            "insight_id": str(row.insight_id) if row.insight_id else "",
            "lineage": row.lineage or {},
        },
        freshness_score=Decimal(str(row.confidence_score or 0)),
        trust_context=trust_context,
    )


@router.get("/operational/status", response_model=AIOperationalStatusResponse)
async def get_ai_operational_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIOperationalStatusResponse:
    report = await AIService(db, current_user.id).operational_status()
    return AIOperationalStatusResponse(
        overall_score=report.overall_score,
        degraded_intelligence_mode=report.degraded_intelligence_mode,
        runs_total=report.runs_total,
        success_rate=report.success_rate,
        pending_approvals=report.pending_approvals,
        avg_confidence=report.avg_confidence,
        recommendations=list(report.recommendations),
    )


@router.get("/costs", response_model=AICostsResponse)
async def get_ai_costs(
    start: str | None = None,
    end: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AICostsResponse:
    from datetime import date

    def _parse(v: str | None) -> date | None:
        return date.fromisoformat(v) if v else None

    report = await AIService(db, current_user.id).costs_report(
        start=_parse(start), end=_parse(end)
    )
    return AICostsResponse(
        period_start=report.period_start,
        period_end=report.period_end,
        runs_total=report.runs_total,
        estimated_cost_usd=report.estimated_cost_usd,
        daily_cap_usd=report.daily_cap_usd,
        daily_spend_usd=report.daily_spend_usd,
        daily_cap_remaining_usd=report.daily_cap_remaining_usd,
        per_run_cap_usd=report.per_run_cap_usd,
        by_workflow=report.by_workflow,
        by_prompt=report.by_prompt,
        by_provider=report.by_provider,
        expensive_runs=report.expensive_runs,
        repeated_prompts=report.repeated_prompts,
        generated_at=report.generated_at,
    )


@router.get("/providers/status", response_model=AIProviderStatusResponse)
async def get_ai_provider_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIProviderStatusResponse:
    status = await AIService(db, current_user.id).provider_status()
    return AIProviderStatusResponse(**status)


@router.get("/usage", response_model=AIUsageResponse)
async def get_ai_usage(
    start: str | None = None,
    end: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIUsageResponse:
    from datetime import date

    def _parse(v: str | None) -> date | None:
        if not v:
            return None
        return date.fromisoformat(v)

    return await AIService(db, current_user.id).usage(start=_parse(start), end=_parse(end))


@router.patch("/recommendations/{recommendation_id}/workflow", response_model=RecommendationResponse)
async def patch_recommendation_workflow(
    recommendation_id: UUID,
    body: RecommendationWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationResponse:
    svc = AIService(db, current_user.id)
    try:
        row = await svc.update_recommendation_workflow(
            recommendation_id,
            action=body.action,
            snooze_days=body.snooze_days or 7,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recommendation not found")
    return RecommendationResponse.model_validate(row)


@router.post(
    "/recommendations/{recommendation_id}/ask",
    response_model=ConversationReplyResponse,
)
async def ask_recommendation(
    recommendation_id: UUID,
    body: RecommendationAskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationReplyResponse:
    reply = await AIService(db, current_user.id).ask_recommendation(
        recommendation_id, question=body.question
    )
    if reply is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recommendation not found")
    return ConversationReplyResponse(
        question=reply.question,
        answer=reply.answer,
        sources=list(reply.sources),
        advisory_only=reply.advisory_only,
    )


@router.get("/todays-focus", response_model=TodaysFocusResponse)
async def get_todays_focus(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodaysFocusResponse:
    focus = await AIService(db, current_user.id).todays_focus()
    return TodaysFocusResponse(
        generated_at=focus.generated_at,
        headline=focus.headline,
        requires_attention_today=list(focus.requires_attention_today),
        can_wait=list(focus.can_wait),
        dangerous=list(focus.dangerous),
        highest_upside=list(focus.highest_upside),
        top_actions=list(focus.top_actions),
        critical_alerts=list(focus.critical_alerts),
        quick_wins=list(focus.quick_wins),
        priority_queue=[
            PriorityQueueItemResponse(
                recommendation_id=i.recommendation_id,
                title=i.title,
                summary=i.summary,
                recommendation_score=i.recommendation_score,
                priority_tier=i.priority_tier,
                priority_score=i.priority_score,
                seller_usefulness=i.seller_usefulness,
            )
            for i in focus.priority_queue
        ],
        advisory_notice=focus.advisory_notice,
    )


@router.get("/digests/{digest_type}", response_model=AIDigestResponse)
async def get_ai_digest(
    digest_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIDigestResponse:
    if digest_type not in ("daily", "weekly", "anomaly"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid digest_type")
    try:
        digest = await AIService(db, current_user.id).generate_digest(digest_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AIDigestResponse(
        digest_type=digest.digest_type,
        generated_at=digest.generated_at,
        headline=digest.headline,
        sections=[
            DigestSectionResponse(title=s.title, body=s.body, priority=s.priority) for s in digest.sections
        ],
        active_recommendation_count=digest.active_recommendation_count,
        advisory_notice=digest.advisory_notice,
    )


@router.get("/usefulness/metrics", response_model=UsefulnessMetricsResponse)
async def get_usefulness_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UsefulnessMetricsResponse:
    m = await AIService(db, current_user.id).usefulness_metrics()
    return UsefulnessMetricsResponse(
        total_recommendations=m.total_recommendations,
        accepted_count=m.accepted_count,
        rejected_count=m.rejected_count,
        ignored_count=m.ignored_count,
        completed_count=m.completed_count,
        dismissed_count=m.dismissed_count,
        saved_count=m.saved_count,
        snoozed_count=m.snoozed_count,
        repeated_fingerprint_count=m.repeated_fingerprint_count,
        fatigue_top_fingerprints=m.fatigue_top_fingerprints,
        action_conversion_rate=m.action_conversion_rate,
        helpful_rate=m.helpful_rate,
        usefulness_score=m.usefulness_score,
        repeated_dismissals=m.repeated_dismissals,
        feedback_trend=m.feedback_trend,
    )


@router.post(
    "/recommendations/{recommendation_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
async def post_recommendation_feedback(
    recommendation_id: UUID,
    body: RecommendationFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    svc = AIService(db, current_user.id)
    rec = await svc.get_recommendation(recommendation_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="recommendation not found")
    await svc.record_feedback(
        recommendation_id,
        rating=body.rating,
        helpful=body.helpful,
        override_reason=body.override_reason,
        feedback_type=body.feedback_type,
    )
    return {"status": "recorded"}

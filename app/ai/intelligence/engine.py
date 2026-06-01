"""AI operational intelligence engine — multi-agent advisory pipeline."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analytics.engine import AIAnalyticsEngine
from app.ai.coordination.coordinator import MultiAgentCoordinator
from app.ai.governance.recommendation_policy import classify_and_gate
from app.ai.memory.strategic import StrategicMemoryStore
from app.ai.metrics import emit_ai_metric
from app.ai.quality.recommendation_quality import QualityResult, apply_quality
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO
from app.dto.ai_intelligence_dto import IntelligenceRunResultDTO
from app.dto.analytics_dto import AIInsightInputDTO
from app.models.ai_intelligence import AIRecommendation, RecommendationStatus, RiskClass


class AIIntelligenceEngine:
    """Phase B entrypoint: analytics run + decision + multi-agent + persistence."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id
        self._analytics = AIAnalyticsEngine(db, user_id)
        self._coordinator = MultiAgentCoordinator()

    async def run_intelligence(
        self,
        request: AIRunRequestDTO,
        *,
        insight_input: AIInsightInputDTO | None = None,
    ) -> IntelligenceRunResultDTO:
        run, validated, insight_id = await self._analytics.execute(
            request, insight_input=insight_input
        )
        from app.ai.context import AIContextAssembler
        from app.ai.grounding.assembler import build_grounded_context

        ctx = await AIContextAssembler(self.db, self.user_id).assemble(
            semantics_version=request.semantics_version,
            insight_input=insight_input,
        )
        grounded = build_grounded_context(ctx)

        result = self._coordinator.coordinate(
            run_id=run.id,
            validated=validated,
            grounded=grounded,
            insight_id=insight_id,
        )

        from app.ai.pipeline.multi_layer import (
            enrich_intelligence_result,
            run_multi_layer_pipeline,
        )

        multi_trace = run_multi_layer_pipeline(
            validated=validated,
            grounded=grounded,
            insight_input=insight_input,
        )
        result = enrich_intelligence_result(
            result,
            validated=validated,
            grounded=grounded,
            insight_input=insight_input,
            multi_trace=multi_trace,
        )

        gated = classify_and_gate(result.recommendation)
        rec = gated.recommendation

        from app.ai.product.fatigue import assess_fatigue
        from app.ai.quality.recommendation_quality import compute_fingerprint

        evidence_ids = tuple(ref.source_id for ref in grounded.evidence)
        fp_preview = compute_fingerprint(
            workflow=validated.workflow.value,
            title=rec.title,
            summary=rec.summary,
            evidence_ids=evidence_ids,
        )
        fatigue = await assess_fatigue(self.db, self.user_id, fp_preview)
        quality = apply_quality(
            scored=rec, validated=validated, grounded=grounded, fatigue=fatigue
        )
        rec = rec.model_copy(
            update={
                "confidence": quality.confidence,
                "priority_score": quality.priority_score,
                "contradictions": list(rec.contradictions) + ([f"quality:{f}" for f in quality.flags]),
            }
        )
        result = result.model_copy(update={"recommendation": rec})

        rec_id = await self._persist_recommendation(
            run.id,
            insight_id,
            result,
            fingerprint=quality.fingerprint,
            quality=quality,
            multi_trace=multi_trace,
        )
        result = result.model_copy(update={"recommendation_id": rec_id})

        await StrategicMemoryStore(self.db, self.user_id).remember(
            memory_key=f"workflow:{request.workflow.value}",
            content=validated.summary[:2000],
            semantics_version=request.semantics_version,
            source_run_id=run.id,
            metadata={"insight_id": str(insight_id) if insight_id else None},
        )

        emit_ai_metric(
            "ai_intelligence_completed",
            run_id=str(run.id),
            recommendation_id=str(rec_id) if rec_id else "",
            confidence=str(rec.confidence),
            requires_approval=rec.requires_human_approval,
        )
        return result

    async def _persist_recommendation(
        self,
        run_id: UUID,
        insight_id: UUID | None,
        result: IntelligenceRunResultDTO,
        *,
        fingerprint: str,
        quality: QualityResult,
        multi_trace=None,
    ) -> UUID | None:
        from app.ai.pipeline.multi_layer import reasoning_trace_payload
        from app.dto.domain_analyst_dto import MultiLayerReasoningTraceDTO

        trace_dto: MultiLayerReasoningTraceDTO | None = multi_trace
        rec = result.recommendation
        status = (
            RecommendationStatus.PENDING_APPROVAL
            if rec.requires_human_approval
            else RecommendationStatus.DRAFT
        )
        row = AIRecommendation(
            user_id=self.user_id,
            run_id=run_id,
            insight_id=insight_id,
            workflow_type=result.action_plan.workflow.value,
            status=status,
            risk_class=RiskClass(rec.risk_class.value),
            title=rec.title[:255],
            summary=rec.summary[:4000],
            confidence_score=float(rec.confidence),
            priority_score=float(rec.priority_score),
            requires_human_approval=rec.requires_human_approval,
            action_plan={
                **result.action_plan.model_dump(mode="json"),
                "why_this_matters": quality.why_this_matters,
                "recommended_action": quality.recommended_action,
                "impact_estimate": quality.impact_estimate,
                "seller_usefulness": quality.seller_usefulness,
            },
            evidence_graph=result.explainability.evidence_graph.model_dump(mode="json"),
            reasoning_trace=(
                reasoning_trace_payload(result, trace_dto)
                if trace_dto is not None
                else {
                    "steps": [s.model_dump(mode="json") for s in result.explainability.reasoning_trace],
                    "agent_messages": [m.model_dump(mode="json") for m in result.agent_messages],
                }
            ),
            lineage={
                "parent_insight_id": str(insight_id) if insight_id else None,
                "fingerprint": fingerprint,
                "novelty_score": quality.seller_usefulness.get("novelty_score"),
                "priority_tier": (quality.seller_usefulness.get("prioritization") or {}).get(
                    "priority_tier"
                ),
                "fatigue_suppressed": (
                    quality.fatigue.should_suppress_duplicate if quality.fatigue else False
                ),
            },
        )
        async with TenantSession.transaction(self.db, self.user_id):
            if quality.fatigue and quality.fatigue.should_suppress_duplicate:
                existing = (
                    await self.db.execute(
                        select(AIRecommendation)
                        .where(AIRecommendation.user_id == self.user_id)
                        .where(AIRecommendation.lineage["fingerprint"].astext == fingerprint)  # type: ignore[attr-defined]
                        .order_by(AIRecommendation.created_at.desc())
                        .limit(1)
                    )
                ).scalars().first()
                if existing is not None:
                    return existing.id
            # Duplicate suppression: if a recent recommendation has the same fingerprint, reuse it.
            existing = (
                await self.db.execute(
                    select(AIRecommendation)
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(AIRecommendation.lineage["fingerprint"].astext == fingerprint)  # type: ignore[attr-defined]
                    .order_by(AIRecommendation.created_at.desc())
                    .limit(1)
                )
            ).scalars().first()
            if existing is not None:
                return existing.id
            self.db.add(row)
            await self.db.flush()
            return row.id

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
        governed_extras: dict | None = None,
    ) -> IntelligenceRunResultDTO:
        run, validated, insight_id = await self._analytics.execute(
            request, insight_input=insight_input
        )
        from app.ai.context import AIContextAssembler
        from app.ai.grounding.assembler import build_grounded_context

        ctx = await AIContextAssembler(self.db, self.user_id).assemble(
            semantics_version=request.semantics_version,
            insight_input=insight_input,
            governed_extras=governed_extras,
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

        from app.ai.insights.composer import compose_insight_driven_output

        snap = dict(grounded.metrics_snapshot or {})
        insight_output = compose_insight_driven_output(
            snap=snap,
            multi_trace=multi_trace,
            llm_title=result.recommendation.title,
            llm_summary=result.recommendation.summary,
        )
        snap["insight_engine"] = insight_output.to_snapshot_payload()
        grounded = grounded.model_copy(update={"metrics_snapshot": snap})

        deep = list(snap.get("deep_insights") or [])
        rec = result.recommendation
        if deep:
            filtered = [
                b
                for b in rec.bullets
                if b not in deep and not str(b).startswith("Top priority")
            ]
            merged_bullets = list(insight_output.bullets) + filtered
        else:
            merged_bullets = list(insight_output.bullets)
        result = result.model_copy(
            update={
                "recommendation": rec.model_copy(
                    update={
                        "title": insight_output.title,
                        "summary": insight_output.summary,
                        "bullets": merged_bullets[:12],
                    }
                )
            }
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
            metrics_snapshot=dict(grounded.metrics_snapshot),
        )
        fatigue = await assess_fatigue(self.db, self.user_id, fp_preview)
        analyst_actions: list[str] = []
        if multi_trace and multi_trace.executive:
            analyst_actions = list(multi_trace.executive.final_recommendations[:5])
        grounded_for_quality = grounded
        if analyst_actions:
            grounded_for_quality = grounded.model_copy(
                update={
                    "metrics_snapshot": {
                        **dict(grounded.metrics_snapshot),
                        "analyst_actions": analyst_actions,
                    }
                }
            )
        quality = apply_quality(
            scored=rec, validated=validated, grounded=grounded_for_quality, fatigue=fatigue
        )
        su = quality.seller_usefulness
        summary_parts: list[str] = []
        snap_for_summary = dict(grounded.metrics_snapshot or {})
        insight_lead = (snap_for_summary.get("insight_engine") or {}).get("executive_lead")
        if insight_lead:
            summary_parts.append(str(insight_lead))
        exec_v2 = su.get("executive_summary_v2_text")
        if exec_v2:
            summary_parts.append(str(exec_v2))
        if not insight_lead:
            summary_parts.append(rec.summary)
        limitations = su.get("analysis_limitations")
        if limitations:
            summary_parts.append(str(limitations))
        ad_warn = su.get("advertising_warning")
        if ad_warn:
            summary_parts.append(str(ad_warn))
        rec = rec.model_copy(
            update={
                "confidence": quality.confidence,
                "priority_score": quality.priority_score,
                "summary": "\n\n".join(summary_parts)[:4000],
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
        from app.dto.domain_analyst_dto import MultiLayerReasoningTraceDTO

        trace_dto: MultiLayerReasoningTraceDTO | None = multi_trace
        rec = result.recommendation
        status = (
            RecommendationStatus.PENDING_APPROVAL
            if rec.requires_human_approval
            else RecommendationStatus.DRAFT
        )
        row = self._build_recommendation_row(
            run_id=run_id,
            insight_id=insight_id,
            result=result,
            rec=rec,
            quality=quality,
            fingerprint=fingerprint,
            status=status,
            trace_dto=trace_dto,
        )
        async with TenantSession.transaction(self.db, self.user_id):
            report_id = quality.seller_usefulness.get("report_id")
            has_compare = bool(
                quality.seller_usefulness.get("requested_compare_period_start")
                or quality.seller_usefulness.get("compare_mode") not in (None, "", "no_compare_data")
            )
            if report_id and not has_compare:
                by_report = (
                    await self.db.execute(
                        select(AIRecommendation)
                        .where(AIRecommendation.user_id == self.user_id)
                        .where(AIRecommendation.lineage["report_id"].astext == str(report_id))  # type: ignore[attr-defined]
                        .limit(1)
                    )
                ).scalars().first()
                if by_report is not None:
                    self._refresh_recommendation(by_report, row)
                    await self.db.flush()
                    return by_report.id
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
                    self._refresh_recommendation(existing, row)
                    await self.db.flush()
                    return existing.id
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
                self._refresh_recommendation(existing, row)
                await self.db.flush()
                return existing.id
            self.db.add(row)
            await self.db.flush()
            return row.id

    @staticmethod
    def _refresh_recommendation(existing: AIRecommendation, fresh: AIRecommendation) -> None:
        """Re-run with the same fingerprint should refresh stored text, not return stale copy."""
        existing.run_id = fresh.run_id
        existing.insight_id = fresh.insight_id
        existing.workflow_type = fresh.workflow_type
        existing.status = fresh.status
        existing.risk_class = fresh.risk_class
        existing.title = fresh.title
        existing.summary = fresh.summary
        existing.confidence_score = fresh.confidence_score
        existing.priority_score = fresh.priority_score
        existing.requires_human_approval = fresh.requires_human_approval
        existing.action_plan = fresh.action_plan
        existing.evidence_graph = fresh.evidence_graph
        existing.reasoning_trace = fresh.reasoning_trace
        existing.lineage = fresh.lineage

    def _build_recommendation_row(
        self,
        *,
        run_id: UUID,
        insight_id: UUID | None,
        result: IntelligenceRunResultDTO,
        rec,
        quality: QualityResult,
        fingerprint: str,
        status: RecommendationStatus,
        trace_dto,
    ) -> AIRecommendation:
        from app.ai.pipeline.multi_layer import reasoning_trace_payload

        return AIRecommendation(
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
                "report_id": quality.seller_usefulness.get("report_id"),
                "fingerprint": fingerprint,
                "novelty_score": quality.seller_usefulness.get("novelty_score"),
                "priority_tier": (quality.seller_usefulness.get("prioritization") or {}).get(
                    "priority_tier"
                ),
                "fatigue_suppressed": (
                    quality.fatigue.should_suppress_duplicate if quality.fatigue else False
                ),
                "compare_period_start": quality.seller_usefulness.get("compare_period_start"),
                "compare_period_end": quality.seller_usefulness.get("compare_period_end"),
                "compare_mode": quality.seller_usefulness.get("compare_mode"),
                "insight_engine_version": "insight_v1",
                "business_coverage_score": (quality.seller_usefulness.get("business_coverage") or {}).get(
                    "business_coverage_score"
                ),
                "insight_quality_score": (quality.seller_usefulness.get("insight_quality") or {}).get("overall"),
                "echo_detected": (quality.seller_usefulness.get("insight_audit") or {}).get("echo_detected"),
            },
        )

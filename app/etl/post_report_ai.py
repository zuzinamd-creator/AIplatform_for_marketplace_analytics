"""Best-effort seller recommendation after successful report ETL."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import get_logger
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, AnalyticsWorkflow
from app.models.ai_insights import AIInsight
from app.models.ai_intelligence import AIRecommendation
from app.models.report import Report, ReportType

logger = get_logger("post_report_ai")


async def _recommendation_exists_for_report(
    db: AsyncSession,
    *,
    user_id: UUID,
    report_id: UUID,
) -> bool:
    async with TenantSession.transaction(db, user_id):
        linked = (
            await db.execute(
                select(AIRecommendation.id)
                .join(AIInsight, AIRecommendation.insight_id == AIInsight.id)
                .where(
                    AIRecommendation.user_id == user_id,
                    AIInsight.context_payload["report_id"].astext == str(report_id),  # type: ignore[index]
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if linked is not None:
            return True
        fp_report = (
            await db.execute(
                select(AIRecommendation.id)
                .where(AIRecommendation.user_id == user_id)
                .where(AIRecommendation.lineage["report_id"].astext == str(report_id))  # type: ignore[index]
                .limit(1)
            )
        ).scalar_one_or_none()
        return fp_report is not None


async def maybe_generate_recommendation_after_report(
    db: AsyncSession,
    *,
    user_id: UUID,
    report_id: UUID,
) -> None:
    """
    Optional post-ETL intelligence hook (legacy auto path).

    Product rule (Phase 9.17-B): AI analysis starts only when the seller
    explicitly runs intelligence (UI «Запустить анализ» / AI API).
    Default ``ai_auto_recommend_after_report=False`` — this hook no-ops.

    Set ``AI_AUTO_RECOMMEND_AFTER_REPORT=true`` only for emergency/legacy
    tenants that still want auto recommendations after finance ETL.
    """
    if not settings.ai_enabled or not settings.ai_auto_recommend_after_report:
        logger.info(
            "post_report_ai_skipped_disabled",
            extra={
                "user_id": str(user_id),
                "report_id": str(report_id),
                "ai_enabled": settings.ai_enabled,
                "ai_auto_recommend_after_report": settings.ai_auto_recommend_after_report,
            },
        )
        return

    async with TenantSession.transaction(db, user_id):
        report = await db.get(Report, report_id)
        if report is None or report.user_id != user_id:
            return
        if report.report_type != ReportType.FINANCE:
            return

    if await _recommendation_exists_for_report(db, user_id=user_id, report_id=report_id):
        logger.info(
            "post_report_ai_skipped_existing",
            extra={"user_id": str(user_id), "report_id": str(report_id)},
        )
        return

    from app.services.ai_service import AIService

    request = AIRunRequestDTO(
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        prompt_id="analytics.summary.v1",
        semantics_version="1.0",
        report_id=report_id,
    )
    try:
        await AIService(db, user_id).run_intelligence(request)
        logger.info(
            "post_report_ai_recommendation_ok",
            extra={"user_id": str(user_id), "report_id": str(report_id)},
        )
    except Exception as exc:
        logger.warning(
            "post_report_ai_recommendation_failed",
            extra={
                "user_id": str(user_id),
                "report_id": str(report_id),
                "error": str(exc)[:500],
            },
        )

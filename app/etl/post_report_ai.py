"""Best-effort seller recommendation after successful report ETL."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import get_logger
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, AnalyticsWorkflow
from app.models.report import Report, ReportType

logger = get_logger("post_report_ai")


async def maybe_generate_recommendation_after_report(
    db: AsyncSession,
    *,
    user_id: UUID,
    report_id: UUID,
) -> None:
    """
    Run revenue_insight intelligence once per processed finance report.

    ETL only creates a pending ai_insights slot; recommendations appear after
    intelligence runs. This hook closes the gap for seller-facing value.
    """
    if not settings.ai_enabled or not settings.ai_auto_recommend_after_report:
        return

    async with TenantSession.transaction(db, user_id):
        report = await db.get(Report, report_id)
        if report is None or report.user_id != user_id:
            return
        if report.report_type != ReportType.FINANCE:
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

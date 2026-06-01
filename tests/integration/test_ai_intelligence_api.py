"""Integration tests for AI intelligence layer."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, AnalyticsWorkflow
from app.models.ai_intelligence import AIRecommendation
from app.models.user import User
from app.services.ai_service import AIService


@pytest.mark.integration
async def test_intelligence_run_persists_recommendation(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"ai-intel-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )

        svc = AIService(session, user_id)
        result = await svc.run_intelligence(
            AIRunRequestDTO(
                workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
                prompt_id="analytics.summary.v1",
            )
        )
        assert result.recommendation_id is not None
        assert result.recommendation.confidence > 0

        await session.rollback()

        async with TenantSession.transaction(session, user_id):
            row = await session.get(AIRecommendation, result.recommendation_id)
        assert row is not None
        assert row.workflow_type == AnalyticsWorkflow.REVENUE_INSIGHT.value

        recs, total = await svc.list_recommendations()
        assert total >= 1

        status = await svc.operational_status()
        assert status.runs_total >= 1

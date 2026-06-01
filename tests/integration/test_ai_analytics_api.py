"""Integration tests for AI analytics engine + persistence."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, AnalyticsWorkflow
from app.models.ai_execution import AIExecutionStatus
from app.models.ai_insights import AIInsight
from app.models.user import User
from app.services.ai_service import AIService


@pytest.mark.integration
async def test_ai_analytics_run_creates_insight(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"ai-api-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )

        svc = AIService(session, user_id)
        run, validated, insight_id = await svc.create_run(
            AIRunRequestDTO(
                workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
                prompt_id="analytics.summary.v1",
            )
        )
        assert run.status in (AIExecutionStatus.SUCCEEDED, AIExecutionStatus.DEGRADED)
        assert insight_id is not None
        assert validated.confidence > 0

        await session.rollback()

        async with TenantSession.transaction(session, user_id):
            row = await session.get(AIInsight, insight_id)
        assert row is not None
        assert row.workflow_type == AnalyticsWorkflow.REVENUE_INSIGHT.value
        assert row.confidence_score is not None

        runs, total = await svc.list_runs()
        assert total >= 1
        assert any(r.id == run.id for r in runs)

"""Integration tests for AI orchestration audit persistence."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.ai.agents import AgentKind, ToolName
from app.ai.orchestration import AIOrchestrationService
from app.core.security_context import TenantSession
from app.dto.analytics_dto import AIInsightInputDTO, ContextDTO, MetricsDTO
from app.models.ai_execution import AIExecutionRun, AIExecutionStatus
from app.models.user import User
from sqlalchemy import select


@pytest.mark.integration
async def test_ai_run_lifecycle_persisted(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"ai-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )

        insight = AIInsightInputDTO(
            context=ContextDTO(
                report_id=uuid4(),
                report_date=date(2026, 2, 1),
                marketplace_type="wildberries",
            ),
            metrics=MetricsDTO(sku_count=2, total_revenue=Decimal("200")),
        )

        svc = AIOrchestrationService(session, user_id)
        run, ctx, trace = await svc.begin_run(
            agent=AgentKind.ANALYTICS,
            prompt_id="analytics.summary.v1",
            insight_input=insight,
            semantics_version="1.0",
        )
        assert ctx.context_valid is True
        svc.invoke_tool(trace, ToolName.READ_ANALYTICS_DTO)
        await svc.complete_run(run, trace, tokens_used=100)

        async with TenantSession.transaction(session, user_id):
            row = await session.get(AIExecutionRun, run.id)
            assert row is not None
            assert row.status in (
                AIExecutionStatus.SUCCEEDED,
                AIExecutionStatus.DEGRADED,
            )
            assert row.tool_call_count == 1
            assert row.tokens_used == 100

            count = (
                await session.execute(
                    select(AIExecutionRun).where(AIExecutionRun.user_id == user_id)
                )
            ).scalars().all()
            assert len(count) == 1

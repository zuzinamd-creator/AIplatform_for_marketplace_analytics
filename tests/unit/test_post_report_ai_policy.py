"""Phase 9.17-B: post-report AI auto-trigger policy."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import settings
from app.etl.post_report_ai import maybe_generate_recommendation_after_report
from app.models.report import ReportType


@pytest.mark.asyncio
async def test_post_report_ai_skipped_when_auto_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_auto_recommend_after_report", False)

    db = MagicMock()
    # AIService is imported lazily inside the hook — patch the service module.
    with patch("app.services.ai_service.AIService") as svc_cls:
        await maybe_generate_recommendation_after_report(
            db,
            user_id=uuid4(),
            report_id=uuid4(),
        )
        svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_post_report_ai_skipped_when_ai_master_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", False)
    monkeypatch.setattr(settings, "ai_auto_recommend_after_report", True)

    db = MagicMock()
    with patch("app.services.ai_service.AIService") as svc_cls:
        await maybe_generate_recommendation_after_report(
            db,
            user_id=uuid4(),
            report_id=uuid4(),
        )
        svc_cls.assert_not_called()


@pytest.mark.asyncio
async def test_post_report_ai_runs_when_auto_explicitly_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ai_auto_recommend_after_report", True)

    user_id = uuid4()
    report_id = uuid4()
    report = MagicMock()
    report.user_id = user_id
    report.report_type = ReportType.FINANCE

    db = MagicMock()
    run_intelligence = AsyncMock()

    class _Txn:
        async def __aenter__(self):
            return db

        async def __aexit__(self, *args):
            return False

    with (
        patch("app.etl.post_report_ai.TenantSession.transaction", return_value=_Txn()),
        patch.object(db, "get", new=AsyncMock(return_value=report)),
        patch(
            "app.etl.post_report_ai._recommendation_exists_for_report",
            new=AsyncMock(return_value=False),
        ),
        patch("app.services.ai_service.AIService") as svc_cls,
    ):
        svc_cls.return_value.run_intelligence = run_intelligence
        await maybe_generate_recommendation_after_report(
            db,
            user_id=user_id,
            report_id=report_id,
        )
        svc_cls.assert_called_once()
        run_intelligence.assert_awaited_once()

"""AI safety: agent kill switch and rate limit."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.agents import AgentKind
from app.ai.policy import AIPolicyViolation, assert_agent_enabled
from app.ai.rate_limit import check_tenant_rate_limit
from app.core.config import settings


def test_disabled_agent_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_disabled_agents", "analytics")
    with pytest.raises(AIPolicyViolation):
        assert_agent_enabled(AgentKind.ANALYTICS)


def test_rate_limit_blocks_burst(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_rate_limit_per_minute", 2)
    uid = uuid4()
    check_tenant_rate_limit(uid)
    check_tenant_rate_limit(uid)
    with pytest.raises(AIPolicyViolation):
        check_tenant_rate_limit(uid)

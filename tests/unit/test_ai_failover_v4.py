"""Provider failover resolution tests."""

from __future__ import annotations

from app.ai.providers.failover import resolve_llm_provider
from app.ai.providers.health import reset_for_tests
from app.core.config import settings


def test_mock_provider_when_configured(monkeypatch) -> None:
    reset_for_tests()
    monkeypatch.setattr(settings, "ai_provider", "mock")
    res = resolve_llm_provider(model="mock")
    assert res.provider_id == "mock"
    assert res.degraded_to_mock is False

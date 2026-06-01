"""Provider adapter unit tests."""

from __future__ import annotations

import pytest
from app.ai.providers.mock import MockEvaluationAdapter, MockLLMAdapter
from app.ai.providers.retry import with_provider_retry
from app.ai.providers.types import EvaluationRequest, LLMMessage, LLMRequest


@pytest.mark.asyncio
async def test_mock_llm_returns_json() -> None:
    adapter = MockLLMAdapter()
    response = await adapter.complete(
        LLMRequest(
            model="mock",
            messages=(LLMMessage(role="user", content="analyze"),),
            metadata={"prompt_id": "analytics.summary.v1"},
        )
    )
    assert "summary" in response.content
    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_provider_retry_succeeds() -> None:
    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RuntimeError("transient")
        return "ok"

    result = await with_provider_retry(flaky, operation_name="test")
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_mock_evaluation_detects_missing_needle() -> None:
    adapter = MockEvaluationAdapter()
    result = await adapter.evaluate(
        EvaluationRequest(
            prompt_id="analytics.summary.v1",
            expected_contains=("advisory_only",),
            actual='{"summary":"x"}',
        )
    )
    assert result.passed is False

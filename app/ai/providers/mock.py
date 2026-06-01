"""Deterministic mock providers for tests and offline development."""

from __future__ import annotations

import json
from time import perf_counter

from app.ai.providers.types import (
    EmbeddingRequest,
    EmbeddingResponse,
    EvaluationRequest,
    EvaluationResult,
    LLMRequest,
    LLMResponse,
    RerankRequest,
    RerankResponse,
)


class MockLLMAdapter:
    provider_name = "mock"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        started = perf_counter()
        prompt_id = request.metadata.get("prompt_id", "unknown")
        payload = {
            "summary": f"Advisory analysis for {prompt_id} (mock).",
            "bullets": ["Grounded in tenant metrics only.", "Not authoritative ledger data."],
            "confidence_hint": 0.85,
            "disclaimer": "advisory_only",
        }
        content = json.dumps(payload, ensure_ascii=False)
        latency = (perf_counter() - started) * 1000
        return LLMResponse(
            content=content,
            model=request.model,
            prompt_tokens=sum(len(m.content) // 4 for m in request.messages),
            completion_tokens=len(content) // 4,
            latency_ms=latency,
            provider=self.provider_name,
            raw={"mock": True},
        )


class MockEmbeddingAdapter:
    provider_name = "mock"

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        started = perf_counter()
        vectors = tuple(
            tuple(hash(text + str(i)) % 1000 / 1000.0 for i in range(8))
            for text in request.texts
        )
        return EmbeddingResponse(
            vectors=vectors,
            model=request.model,
            latency_ms=(perf_counter() - started) * 1000,
            provider=self.provider_name,
        )


class MockRerankAdapter:
    provider_name = "mock"

    async def rerank(self, request: RerankRequest) -> RerankResponse:
        started = perf_counter()
        indices = tuple(range(min(request.top_k, len(request.documents))))
        scores = tuple(1.0 - (i * 0.1) for i in indices)
        return RerankResponse(
            ranked_indices=indices,
            scores=scores,
            latency_ms=(perf_counter() - started) * 1000,
            provider=self.provider_name,
        )


class MockEvaluationAdapter:
    provider_name = "mock"

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult:
        failures = tuple(
            needle for needle in request.expected_contains if needle not in request.actual
        )
        score = 1.0 if not failures else max(0.0, 1.0 - len(failures) * 0.25)
        return EvaluationResult(passed=not failures, score=score, failures=failures)

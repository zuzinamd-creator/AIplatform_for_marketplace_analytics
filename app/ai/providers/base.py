"""Provider adapter protocols."""

from __future__ import annotations

from typing import Protocol

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


class LLMAdapter(Protocol):
    provider_name: str

    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    # Optional streaming API (OpenAI-compatible SSE).
    async def stream(self, request: LLMRequest): ...  # pragma: no cover


class EmbeddingAdapter(Protocol):
    provider_name: str

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...


class RerankAdapter(Protocol):
    provider_name: str

    async def rerank(self, request: RerankRequest) -> RerankResponse: ...


class EvaluationAdapter(Protocol):
    provider_name: str

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult: ...

"""Provider factory — delegates to failover resolver (REAL-AI-V4A)."""

from __future__ import annotations

from typing import cast

from app.ai.providers.base import (
    EmbeddingAdapter,
    EvaluationAdapter,
    LLMAdapter,
    RerankAdapter,
)
from app.ai.providers.failover import resolve_llm_provider
from app.ai.providers.mock import (
    MockEmbeddingAdapter,
    MockEvaluationAdapter,
    MockRerankAdapter,
)
from app.ai.providers.model_router import ModelRole, resolve_model


def get_llm_adapter(*, model: str | None = None, role: ModelRole | None = None) -> LLMAdapter:
    model_name, _ = resolve_model(role=role)
    if model:
        model_name = model
    resolution = resolve_llm_provider(model=model_name)
    return cast(LLMAdapter, resolution.adapter)


def get_llm_resolution(*, workflow: str, streaming: bool = False):
    """Full resolution including provider metadata for audit."""
    from app.ai.providers.model_router import resolve_model, role_for_workflow

    role = role_for_workflow(workflow, streaming=streaming)
    model, role_used = resolve_model(role=role, workflow=workflow, streaming=streaming)
    res = resolve_llm_provider(model=model)
    return res, role_used, model


def get_embedding_adapter() -> EmbeddingAdapter:
    from app.ai.providers.model_router import ModelRole, resolve_model
    from app.core.config import settings

    if settings.ai_provider == "mock":
        return MockEmbeddingAdapter()
    model, _ = resolve_model(role=ModelRole.CHEAP)
    return MockEmbeddingAdapter()


def get_rerank_adapter() -> RerankAdapter:
    return MockRerankAdapter()


def get_evaluation_adapter() -> EvaluationAdapter:
    return MockEvaluationAdapter()

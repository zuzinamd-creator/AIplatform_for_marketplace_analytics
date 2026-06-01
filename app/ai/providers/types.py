"""Provider request/response types (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    model: str
    messages: tuple[LLMMessage, ...]
    max_tokens: int = 1024
    temperature: float = 0.2
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    provider: str
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMStreamEvent:
    """Streaming event for SSE-compatible providers."""

    type: str  # "delta" | "final"
    delta: str = ""
    raw: dict[str, Any] | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
    model: str


@dataclass(frozen=True)
class EmbeddingResponse:
    vectors: tuple[tuple[float, ...], ...]
    model: str
    latency_ms: float
    provider: str


@dataclass(frozen=True)
class RerankRequest:
    query: str
    documents: tuple[str, ...]
    model: str
    top_k: int = 5


@dataclass(frozen=True)
class RerankResponse:
    ranked_indices: tuple[int, ...]
    scores: tuple[float, ...]
    latency_ms: float
    provider: str


@dataclass(frozen=True)
class EvaluationRequest:
    prompt_id: str
    expected_contains: tuple[str, ...]
    actual: str


@dataclass(frozen=True)
class EvaluationResult:
    passed: bool
    score: float
    failures: tuple[str, ...]

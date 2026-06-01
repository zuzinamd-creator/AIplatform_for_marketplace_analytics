"""Provider resolution with failover, circuit breaker, and graceful degradation."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.metrics import emit_ai_metric
from app.ai.providers.health import record_failover, record_failure, record_success, snapshot
from app.ai.providers.mock import MockLLMAdapter
from app.ai.providers.openai_compatible import OpenAICompatibleLLMAdapter
from app.ai.providers.provider_profiles import (
    ProviderCredentials,
    resolve_failover_credentials,
    resolve_primary_credentials,
)
from app.core.config import settings
from app.runtime.reliability.circuit_breaker import GLOBAL_CIRCUIT_BREAKERS


@dataclass(frozen=True)
class ProviderResolution:
    adapter: object  # LLMAdapter | OpenAICompatibleLLMAdapter | MockLLMAdapter
    provider_id: str
    model: str
    used_failover: bool
    degraded_to_mock: bool
    credentials_source: str


def _adapter_from_creds(creds: ProviderCredentials) -> OpenAICompatibleLLMAdapter:
    return OpenAICompatibleLLMAdapter(
        base_url=creds.base_url,
        api_key=creds.api_key,
        timeout_seconds=float(settings.ai_request_timeout_seconds),
        provider_label=creds.provider_id,
    )


def resolve_llm_provider(*, model: str) -> ProviderResolution:
    """Select LLM adapter: primary → failover → mock (degraded)."""
    if not GLOBAL_CIRCUIT_BREAKERS.allow("ai_provider"):
        emit_ai_metric("ai_provider_circuit_open")
        return ProviderResolution(
            adapter=MockLLMAdapter(),
            provider_id="mock",
            model="mock",
            used_failover=False,
            degraded_to_mock=True,
            credentials_source="circuit_open",
        )

    primary_name = settings.ai_provider.lower()
    if primary_name == "mock":
        return ProviderResolution(
            adapter=MockLLMAdapter(),
            provider_id="mock",
            model="mock",
            used_failover=False,
            degraded_to_mock=False,
            credentials_source="configured_mock",
        )

    primary = resolve_primary_credentials()
    if primary is not None:
        try:
            adapter = _adapter_from_creds(primary)
            return ProviderResolution(
                adapter=adapter,
                provider_id=primary.provider_id,
                model=model or primary.default_model,
                used_failover=False,
                degraded_to_mock=False,
                credentials_source="primary",
            )
        except Exception as exc:
            record_failure(primary.provider_id, str(exc))
            emit_ai_metric("ai_provider_primary_failed", error=str(exc)[:200])

    failover = resolve_failover_credentials()
    if failover is not None:
        try:
            record_failover(primary_name, failover.provider_id)
            emit_ai_metric(
                "ai_provider_failover",
                primary=primary_name,
                failover=failover.provider_id,
            )
            adapter = _adapter_from_creds(failover)
            return ProviderResolution(
                adapter=adapter,
                provider_id=failover.provider_id,
                model=model or failover.default_model,
                used_failover=True,
                degraded_to_mock=False,
                credentials_source="failover",
            )
        except Exception as exc:
            record_failure(failover.provider_id, str(exc))

    emit_ai_metric("ai_provider_degraded_mock")
    return ProviderResolution(
        adapter=MockLLMAdapter(),
        provider_id="mock",
        model="mock",
        used_failover=bool(failover),
        degraded_to_mock=True,
        credentials_source="degraded_mock",
    )


def mark_provider_success(provider_id: str) -> None:
    record_success(provider_id)
    GLOBAL_CIRCUIT_BREAKERS.success("ai_provider")


def mark_provider_failure(provider_id: str, error: str) -> None:
    record_failure(provider_id, error)
    GLOBAL_CIRCUIT_BREAKERS.failure("ai_provider")


def provider_status_payload() -> dict:
    circuit_open = not GLOBAL_CIRCUIT_BREAKERS.allow("ai_provider")
    return {
        "primary_provider": settings.ai_provider,
        "failover_provider": settings.ai_failover_provider or None,
        "circuit_breaker_open": circuit_open,
        "streaming_enabled": settings.ai_enable_streaming,
        "cost_tracking_enabled": settings.ai_enable_cost_tracking,
        "prompt_runtime_version": settings.ai_prompt_runtime_version,
        "providers": snapshot(),
    }

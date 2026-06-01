"""OpenAI-compatible provider profile resolution."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings

# Named providers map to default base URLs (override via AI_*_BASE_URL).
KNOWN_OPENAI_COMPAT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com",
    "together": "https://api.together.xyz/v1",
    "ollama": "http://localhost:11434/v1",
}


@dataclass(frozen=True)
class ProviderCredentials:
    provider_id: str
    base_url: str
    api_key: str
    default_model: str


def resolve_primary_credentials() -> ProviderCredentials | None:
    return _resolve_named(settings.ai_provider, primary=True)


def resolve_failover_credentials() -> ProviderCredentials | None:
    name = settings.ai_failover_provider.strip()
    if not name:
        return None
    return _resolve_named(name, primary=False)


def _resolve_named(name: str, *, primary: bool) -> ProviderCredentials | None:
    key = name.lower().strip()
    if key in ("", "mock"):
        return None
    if key == "openai_compatible":
        base = settings.ai_openai_base_url if primary else settings.ai_failover_base_url
        api_key = settings.ai_openai_api_key if primary else settings.ai_failover_api_key
        model = settings.ai_openai_model if primary else (settings.ai_failover_model or settings.ai_openai_model)
        if not base or not api_key:
            return None
        return ProviderCredentials(key, base.rstrip("/"), api_key, model)

    base_default = KNOWN_OPENAI_COMPAT_BASE_URLS.get(key)
    if primary:
        base = settings.ai_openai_base_url or base_default or ""
        api_key = settings.ai_openai_api_key
        model = settings.ai_openai_model
    else:
        base = settings.ai_failover_base_url or base_default or ""
        api_key = settings.ai_failover_api_key or settings.ai_openai_api_key
        model = settings.ai_failover_model or settings.ai_openai_model

    if not api_key:
        return None
    if not base:
        return None
    return ProviderCredentials(key, base.rstrip("/"), api_key, model)

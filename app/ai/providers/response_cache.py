"""Optional in-memory response cache for identical governed prompts."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class CacheEntry:
    content: str
    expires_at: float


_cache: dict[str, CacheEntry] = {}


def _enabled() -> bool:
    return settings.ai_enable_response_cache and settings.ai_cache_ttl_seconds > 0


def cache_key(*, system: str, user: str, model: str) -> str:
    payload = json.dumps({"s": system[:2000], "u": user[:4000], "m": model}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def get(key: str) -> str | None:
    if not _enabled():
        return None
    entry = _cache.get(key)
    if entry is None:
        return None
    if time.time() > entry.expires_at:
        _cache.pop(key, None)
        return None
    return entry.content


def set(key: str, content: str) -> None:
    if not _enabled():
        return
    _cache[key] = CacheEntry(
        content=content,
        expires_at=time.time() + float(settings.ai_cache_ttl_seconds),
    )


def clear_for_tests() -> None:
    _cache.clear()

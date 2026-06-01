"""Retry wrapper for provider calls (bounded, audit-friendly)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core.config import settings


async def with_provider_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    operation_name: str,
) -> T:
    # Prefer new name (AI_MAX_RETRIES) but keep backwards compatibility.
    max_retries = getattr(settings, "ai_max_retries", settings.ai_provider_max_retries)
    attempts = max(1, int(max_retries) + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            await asyncio.sleep(min(2**attempt * 0.25, 2.0))
    assert last_error is not None
    raise RuntimeError(f"{operation_name} failed after {attempts} attempts") from last_error

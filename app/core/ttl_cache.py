"""Simple in-process TTL cache for read-heavy endpoints (single-instance advisory)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TtlCache(Generic[T]):
    def __init__(self, *, ttl_seconds: float, max_entries: int = 512) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._lock = Lock()
        self._entries: dict[str, _Entry[T]] = {}

    def get(self, key: str) -> T | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                del self._entries[key]
                return None
            return entry.value

    def set(self, key: str, value: T) -> None:
        expires_at = time.monotonic() + self._ttl
        with self._lock:
            if len(self._entries) >= self._max_entries:
                self._evict_expired_locked(time.monotonic())
            self._entries[key] = _Entry(value=value, expires_at=expires_at)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys = [k for k in self._entries if k.startswith(prefix)]
            for key in keys:
                del self._entries[key]

    def _evict_expired_locked(self, now: float) -> None:
        expired = [k for k, v in self._entries.items() if v.expires_at <= now]
        for key in expired:
            del self._entries[key]
        if len(self._entries) >= self._max_entries:
            oldest = min(self._entries.items(), key=lambda item: item[1].expires_at)[0]
            del self._entries[oldest]

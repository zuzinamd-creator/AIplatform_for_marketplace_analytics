"""Per-tenant AI rate limiting (in-process; advisory gate before runs)."""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from uuid import UUID

from app.ai.policy import AIPolicyViolation
from app.core.config import settings

_lock = Lock()
_windows: dict[str, list[float]] = defaultdict(list)
_global_hits: list[float] = []


def check_tenant_rate_limit(user_id: UUID) -> None:
    if settings.ai_rate_limit_per_minute <= 0:
        return
    key = str(user_id)
    now_mono = time.monotonic()
    now_wall = time.time()
    window_start = now_mono - 60.0
    hour_start = now_wall - 3600.0
    with _lock:
        _global_hits[:] = [t for t in _global_hits if t >= hour_start]
        if len(_global_hits) >= settings.reliability_ai_runaway_per_hour:
            raise AIPolicyViolation("platform AI runaway containment active")
        hits = [t for t in _windows[key] if t >= window_start]
        if len(hits) >= settings.ai_rate_limit_per_minute:
            raise AIPolicyViolation("AI rate limit exceeded for tenant")
        hits.append(now_mono)
        _global_hits.append(now_wall)
        _windows[key] = hits

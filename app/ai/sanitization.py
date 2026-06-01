"""Prompt-injection resistance for user-controlled strings."""

from __future__ import annotations

import re

_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\s*/?\s*script", re.I),
)


def sanitize_user_text(text: str, *, max_length: int = 4000) -> str:
    cleaned = text.replace("\x00", "").strip()[:max_length]
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)
    return cleaned

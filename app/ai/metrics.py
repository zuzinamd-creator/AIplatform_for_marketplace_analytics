"""AI execution observability (structured logs)."""

from __future__ import annotations

from typing import Any

from app.core.observability import get_logger

logger = get_logger("ai_execution")


def emit_ai_metric(event: str, **fields: Any) -> None:
    payload = {k: v for k, v in fields.items() if v is not None}
    logger.info(event, extra=payload)

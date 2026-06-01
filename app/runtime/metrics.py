"""Structured runtime metrics (JSON logs only)."""

from __future__ import annotations

from typing import Any

from app.core.observability import get_logger

logger = get_logger("runtime_metrics")


def emit_runtime_metric(event: str, **fields: Any) -> None:
    payload = {k: v for k, v in fields.items() if v is not None}
    logger.info(event, extra=payload)

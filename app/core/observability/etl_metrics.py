"""Structured ETL/DB metric fields for JSON logs."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Any

_metrics: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "etl_metrics",
    default=None,
)
_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("log_user_id", default=None)
_operation_stage: contextvars.ContextVar[str | None] = contextvars.ContextVar("operation_stage", default=None)
_semantics_version: contextvars.ContextVar[str | None] = contextvars.ContextVar("semantics_version", default=None)
_rebuild_window: contextvars.ContextVar[str | None] = contextvars.ContextVar("rebuild_window", default=None)


def bind_log_context(
    *,
    user_id: str | None = None,
    operation_stage: str | None = None,
    semantics_version: str | None = None,
    rebuild_window: str | None = None,
) -> None:
    if user_id is not None:
        _user_id.set(user_id)
    if operation_stage is not None:
        _operation_stage.set(operation_stage)
    if semantics_version is not None:
        _semantics_version.set(semantics_version)
    if rebuild_window is not None:
        _rebuild_window.set(rebuild_window)


def record_metrics(**fields: Any) -> None:
    current = dict(_metrics.get() or {})
    current.update({key: value for key, value in fields.items() if value is not None})
    _metrics.set(current)


def metrics_context() -> dict[str, Any]:
    ctx = dict(_metrics.get() or {})
    if _user_id.get():
        ctx["user_id"] = _user_id.get()
    if _operation_stage.get():
        ctx["operation_stage"] = _operation_stage.get()
    if _semantics_version.get():
        ctx["semantics_version"] = _semantics_version.get()
    if _rebuild_window.get():
        ctx["rebuild_window"] = _rebuild_window.get()
    return ctx


@contextmanager
def track_rebuild(*, mode: str, user_id: str, rebuild_window: str, semantics_version: str = "1.0"):
    import time

    from app.core.observability import get_logger

    logger = get_logger(__name__)
    bind_log_context(
        user_id=user_id,
        operation_stage="rebuild",
        semantics_version=semantics_version,
        rebuild_window=rebuild_window,
    )
    started = time.perf_counter()
    record_metrics(rebuild_full_vs_incremental=mode)
    try:
        yield
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        record_metrics(rebuild_duration_ms=duration_ms)
        from app.operations.safety_guards import warn_rebuild_duration_high

        warn_rebuild_duration_high(
            duration_ms=duration_ms,
            user_id=user_id,
            rebuild_mode=mode,
        )
        logger.info("inventory_rebuild_complete", extra=metrics_context())
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        record_metrics(rebuild_duration_ms=duration_ms)
        from app.operations.safety_guards import warn_rebuild_duration_high

        warn_rebuild_duration_high(
            duration_ms=duration_ms,
            user_id=user_id,
            rebuild_mode=mode,
        )
        logger.exception(
            "inventory_rebuild_failed",
            extra={**metrics_context(), "error": str(exc)},
        )
        raise

import contextvars
import time
import uuid
from contextlib import contextmanager
from typing import Any

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id",
    default=None,
)
_job_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)
_report_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("report_id", default=None)


def set_correlation_id(value: str | None = None) -> str:
    correlation_id = value or str(uuid.uuid4())
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def bind_job_context(*, job_id: str, report_id: str) -> None:
    _job_id.set(job_id)
    _report_id.set(report_id)


def clear_context() -> None:
    _correlation_id.set(None)
    _job_id.set(None)
    _report_id.set(None)


def logging_context() -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    if _correlation_id.get():
        ctx["correlation_id"] = _correlation_id.get()
    if _job_id.get():
        ctx["job_id"] = _job_id.get()
    if _report_id.get():
        ctx["report_id"] = _report_id.get()
    return ctx


@contextmanager
def track_duration(logger, event: str, **fields: Any):
    started = time.perf_counter()
    try:
        yield
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(event, extra={"duration_ms": duration_ms, "status": "ok", **fields})
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            event,
            extra={"duration_ms": duration_ms, "status": "error", "error": str(exc), **fields},
        )
        raise

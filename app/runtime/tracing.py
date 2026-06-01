"""Runtime tracing helpers — rebuild trace IDs and correlation."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.observability.context import get_correlation_id
from app.runtime.metrics import emit_runtime_metric


def new_rebuild_trace_id() -> UUID:
    return uuid4()


def bind_rebuild_trace(
    *,
    trace_id: UUID,
    requirement_id: UUID,
    user_id: UUID,
) -> None:
    emit_runtime_metric(
        "runtime_rebuild_trace",
        rebuild_trace_id=str(trace_id),
        requirement_id=str(requirement_id),
        user_id=str(user_id),
        correlation_id=get_correlation_id(),
    )

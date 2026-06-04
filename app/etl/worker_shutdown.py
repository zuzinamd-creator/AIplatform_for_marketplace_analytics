"""Graceful worker shutdown signalling (SIGINT/SIGTERM)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

ShutdownCheck = Callable[[], bool]

# Legacy .xls path loads full file into RAM — hard cap before read.
LEGACY_XLS_MAX_BYTES = 50 * 1024 * 1024

LEGACY_XLS_TOO_LARGE_MESSAGE = (
    "Файл слишком большой для старого формата, конвертируйте в .xlsx"
)


class LegacyReportTooLargeError(ValueError):
    """Raised when a legacy .xls report exceeds LEGACY_XLS_MAX_BYTES."""


class WorkerShutdownRequested(Exception):
    """
    Worker received SIGTERM/SIGINT.

    The current chunk must already be committed by the caller; no new chunks
    should be started after this exception.
    """

    def __init__(
        self,
        *,
        phase: str,
        chunks_completed: int = 0,
        message: str = "Worker shutdown requested",
    ) -> None:
        self.phase = phase
        self.chunks_completed = chunks_completed
        super().__init__(message)


def default_shutdown_check() -> ShutdownCheck | None:
    """Bind to the running ETL worker shutdown event, if available."""
    try:
        from app.etl import worker

        return worker.is_shutdown_requested
    except (ImportError, AttributeError):
        return None


def is_shutdown(check: ShutdownCheck | None) -> bool:
    return bool(check and check())

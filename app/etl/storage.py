from collections.abc import AsyncIterator, Iterator
from pathlib import Path

from app.core.config import settings
from app.etl.worker_shutdown import (
    LEGACY_XLS_MAX_BYTES,
    LEGACY_XLS_TOO_LARGE_MESSAGE,
    LegacyReportTooLargeError,
)
from app.storage import get_report_storage


def save_report_file(user_id: str, report_id: str, filename: str, chunks: Iterator[bytes]) -> str:
    """Save report via primary storage backend; returns storage URI."""
    return get_report_storage().save_stream(user_id, report_id, filename, chunks)


async def save_report_upload(
    user_id: str,
    report_id: str,
    filename: str,
    stream: AsyncIterator[bytes],
) -> str:
    return await get_report_storage().save_upload_stream(user_id, report_id, filename, stream)


def iter_report_file(storage_uri: str, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    return get_report_storage().iter_chunks(storage_uri, chunk_size=chunk_size)


def read_report_file(storage_uri: str, *, filename: str | None = None) -> bytes:
    """Bounded read for ETL pipeline (existing bytes contract)."""
    max_bytes = settings.max_upload_bytes
    if filename and Path(filename).suffix.lower() == ".xls":
        max_bytes = min(max_bytes, LEGACY_XLS_MAX_BYTES)
    try:
        return get_report_storage().read_all(storage_uri, max_bytes=max_bytes)
    except ValueError as exc:
        if filename and Path(filename).suffix.lower() == ".xls":
            raise LegacyReportTooLargeError(LEGACY_XLS_TOO_LARGE_MESSAGE) from exc
        raise

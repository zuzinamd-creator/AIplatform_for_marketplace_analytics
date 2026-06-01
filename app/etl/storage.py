from collections.abc import AsyncIterator, Iterator

from app.core.config import settings
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


def read_report_file(storage_uri: str) -> bytes:
    """Bounded read for ETL pipeline (existing bytes contract)."""
    return get_report_storage().read_all(storage_uri, max_bytes=settings.max_upload_bytes)

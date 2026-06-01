from collections.abc import AsyncIterator, Iterator
from typing import Protocol


class ReportStorage(Protocol):
    """Object storage abstraction (Supabase/S3 primary, local dev fallback)."""

    def save_stream(
        self,
        user_id: str,
        report_id: str,
        filename: str,
        chunks: Iterator[bytes],
    ) -> str:
        """Persist file from chunked iterator; return storage URI."""
        ...

    async def save_upload_stream(
        self,
        user_id: str,
        report_id: str,
        filename: str,
        stream: AsyncIterator[bytes],
    ) -> str:
        """Async variant for FastAPI UploadFile streaming."""
        ...

    def iter_chunks(self, storage_uri: str, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        """Stream file content without loading entire object into RAM."""
        ...

    def read_all(self, storage_uri: str, *, max_bytes: int) -> bytes:
        """Bounded read for ETL pipeline compatibility."""
        ...

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

from app.core.config import settings


class LocalReportStorage:
    """Development-only fallback when remote storage is unavailable."""

    def _path(self, user_id: str, report_id: str, filename: str) -> Path:
        return Path(settings.uploads_dir) / user_id / report_id / filename

    def save_stream(
        self,
        user_id: str,
        report_id: str,
        filename: str,
        chunks: Iterator[bytes],
    ) -> str:
        target = self._path(user_id, report_id, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            for chunk in chunks:
                if chunk:
                    handle.write(chunk)
        return str(target)

    async def save_upload_stream(
        self,
        user_id: str,
        report_id: str,
        filename: str,
        stream: AsyncIterator[bytes],
    ) -> str:
        target = self._path(user_id, report_id, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            async for chunk in stream:
                if chunk:
                    handle.write(chunk)
        return str(target)

    def iter_chunks(self, storage_uri: str, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        path = Path(storage_uri)
        with path.open("rb") as handle:
            while True:
                data = handle.read(chunk_size)
                if not data:
                    break
                yield data

    def read_all(self, storage_uri: str, *, max_bytes: int) -> bytes:
        buffer = bytearray()
        for chunk in self.iter_chunks(storage_uri):
            buffer.extend(chunk)
            if len(buffer) > max_bytes:
                raise ValueError(f"File exceeds max allowed size ({max_bytes} bytes)")
        return bytes(buffer)

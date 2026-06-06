import re
from collections.abc import AsyncIterator, Iterator
from io import BytesIO
from pathlib import Path

import httpx

from app.core.config import settings
from app.integrations.supabase_client import get_supabase_client

_ALLOWED_EXTENSIONS = frozenset({".xlsx", ".xls", ".csv"})


def storage_object_name(filename: str, report_id: str) -> str:
    """ASCII-safe object key for Supabase/S3 (original filename stays in DB)."""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        ext = ".bin"
    return f"{report_id}{ext}"


def is_ascii_storage_key(path: str) -> bool:
    """True when every path segment is safe for Supabase/S3 object keys."""
    if not path or path.startswith("/") or ".." in path.split("/"):
        return False
    allowed = re.compile(r"^[A-Za-z0-9._-]+$")
    return all(allowed.match(part) for part in path.split("/") if part)


class SupabaseReportStorage:
    """Primary production storage via Supabase Storage (S3-compatible API)."""

    def _object_path(self, user_id: str, report_id: str, filename: str) -> tuple[str, str]:
        bucket = settings.supabase_storage_bucket
        path = f"{user_id}/{report_id}/{storage_object_name(filename, report_id)}"
        return bucket, path

    def _uri(self, bucket: str, path: str) -> str:
        return f"{bucket}/{path}"

    def save_stream(
        self,
        user_id: str,
        report_id: str,
        filename: str,
        chunks: Iterator[bytes],
    ) -> str:
        client = get_supabase_client()
        if client is None:
            raise RuntimeError("Supabase client is not configured")

        bucket, path = self._object_path(user_id, report_id, filename)
        buffer = BytesIO()
        for chunk in chunks:
            if chunk:
                buffer.write(chunk)
        buffer.seek(0)
        client.storage.from_(bucket).upload(
            path,
            buffer.getvalue(),
            file_options={"content-type": "application/octet-stream", "upsert": "true"},
        )
        return self._uri(bucket, path)

    async def save_upload_stream(
        self,
        user_id: str,
        report_id: str,
        filename: str,
        stream: AsyncIterator[bytes],
    ) -> str:
        buffer = BytesIO()
        async for chunk in stream:
            if chunk:
                buffer.write(chunk)

        def _iter() -> Iterator[bytes]:
            buffer.seek(0)
            while True:
                data = buffer.read(1024 * 1024)
                if not data:
                    break
                yield data

        return self.save_stream(user_id, report_id, filename, _iter())

    def iter_chunks(self, storage_uri: str, *, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
        """HTTP stream from signed URL — avoids loading the full object into RAM."""
        client = get_supabase_client()
        if client is None:
            raise RuntimeError("Supabase client is not configured")

        bucket, path = storage_uri.split("/", 1)
        signed = client.storage.from_(bucket).create_signed_url(path, 3600)
        signed_url = signed.get("signedURL") or signed.get("signedUrl")
        if not signed_url:
            raise RuntimeError(f"Failed to sign download URL for {storage_uri}")

        total = 0
        timeout = httpx.Timeout(600.0, connect=30.0)
        with httpx.Client(timeout=timeout, follow_redirects=True) as http:
            with http.stream("GET", signed_url) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > settings.max_upload_bytes:
                        raise ValueError(
                            f"File exceeds max allowed size ({settings.max_upload_bytes} bytes)"
                        )
                    yield chunk

    def read_all(self, storage_uri: str, *, max_bytes: int) -> bytes:
        buffer = bytearray()
        for chunk in self.iter_chunks(storage_uri):
            buffer.extend(chunk)
            if len(buffer) > max_bytes:
                raise ValueError(f"File exceeds max allowed size ({max_bytes} bytes)")
        return bytes(buffer)

    def delete(self, storage_uri: str) -> None:
        client = get_supabase_client()
        if client is None:
            return
        bucket, path = storage_uri.split("/", 1)
        try:
            client.storage.from_(bucket).remove([path])
        except Exception:
            return

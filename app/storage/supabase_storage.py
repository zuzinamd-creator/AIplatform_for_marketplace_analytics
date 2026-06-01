from collections.abc import AsyncIterator, Iterator
from io import BytesIO

from app.core.config import settings
from app.integrations.supabase_client import get_supabase_client


class SupabaseReportStorage:
    """Primary production storage via Supabase Storage (S3-compatible API)."""

    def _object_path(self, user_id: str, report_id: str, filename: str) -> tuple[str, str]:
        bucket = settings.supabase_storage_bucket
        path = f"{user_id}/{report_id}/{filename}"
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
        client = get_supabase_client()
        if client is None:
            raise RuntimeError("Supabase client is not configured")

        bucket, path = storage_uri.split("/", 1)
        payload = client.storage.from_(bucket).download(path)
        offset = 0
        while offset < len(payload):
            yield payload[offset : offset + chunk_size]
            offset += chunk_size

    def read_all(self, storage_uri: str, *, max_bytes: int) -> bytes:
        chunks = list(self.iter_chunks(storage_uri))
        content = b"".join(chunks)
        if len(content) > max_bytes:
            raise ValueError(f"File exceeds max allowed size ({max_bytes} bytes)")
        return content

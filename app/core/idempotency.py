import hashlib
from collections.abc import AsyncIterator, Iterable

CHUNK_SIZE = 1024 * 1024


def streaming_checksum(chunks: Iterable[bytes]) -> str:
    """Memory-safe SHA-256 over chunked byte iterables."""
    digest = hashlib.sha256()
    for chunk in chunks:
        if chunk:
            digest.update(chunk)
    return digest.hexdigest()


async def async_streaming_checksum(stream: AsyncIterator[bytes]) -> str:
    digest = hashlib.sha256()
    async for chunk in stream:
        if chunk:
            digest.update(chunk)
    return digest.hexdigest()


def file_checksum(content: bytes) -> str:
    """Backward-compatible helper for small in-memory payloads."""
    return hashlib.sha256(content).hexdigest()

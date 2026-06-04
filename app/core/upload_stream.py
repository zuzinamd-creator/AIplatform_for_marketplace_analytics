import hashlib
import tempfile
from collections.abc import Iterator

from fastapi import UploadFile

from app.core.config import settings
from app.core.idempotency import CHUNK_SIZE


class SpooledUpload:
    """Single-pass network read; checksum + replay from spooled temp file."""

    def __init__(self, checksum: str, spool: tempfile.SpooledTemporaryFile, *, size_bytes: int):
        self.checksum = checksum
        self._spool = spool
        self.size_bytes = size_bytes

    def iter_chunks(self) -> Iterator[bytes]:
        self._spool.seek(0)
        while True:
            data = self._spool.read(CHUNK_SIZE)
            if not data:
                break
            yield data

    def read_all(self) -> bytes:
        return b"".join(self.iter_chunks())


async def buffer_upload_with_checksum(file: UploadFile) -> SpooledUpload:
    digest = hashlib.sha256()
    spool = tempfile.SpooledTemporaryFile(max_size=settings.upload_spool_max_bytes)
    size_bytes = 0

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        digest.update(chunk)
        spool.write(chunk)
        size_bytes += len(chunk)

    spool.seek(0)
    return SpooledUpload(digest.hexdigest(), spool, size_bytes=size_bytes)

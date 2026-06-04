"""Stream report objects from storage to a temp file (bounded RAM)."""

from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings
from app.storage import get_report_storage


class ReportChecksumMismatchError(ValueError):
    """Downloaded file digest does not match report metadata."""


@contextmanager
def materialize_report_file(
    storage_uri: str,
    *,
    suffix: str = ".xlsx",
    expected_checksum: str | None = None,
) -> Iterator[Path]:
    """
    Download storage object to a temp file in chunks; delete on exit.

    Local dev paths are used in place (no copy). Caller must close parsers before exit.
    """
    local = Path(storage_uri)
    if local.is_file():
        if expected_checksum:
            digest = hashlib.sha256()
            with local.open("rb") as handle:
                while True:
                    block = handle.read(1024 * 1024)
                    if not block:
                        break
                    digest.update(block)
            if digest.hexdigest() != expected_checksum:
                raise ReportChecksumMismatchError("Report file checksum mismatch")
        yield local
        return

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    path = Path(tmp.name)
    tmp.close()
    total = 0
    digest = hashlib.sha256()
    try:
        storage = get_report_storage()
        for chunk in storage.iter_chunks(storage_uri, chunk_size=1024 * 1024):
            if not chunk:
                continue
            digest.update(chunk)
            total += len(chunk)
            if total > settings.max_upload_bytes:
                raise ValueError(f"File exceeds max allowed size ({settings.max_upload_bytes} bytes)")
            with path.open("ab") as handle:
                handle.write(chunk)
        if total == 0:
            raise ValueError("Report file is empty")
        if expected_checksum and digest.hexdigest() != expected_checksum:
            raise ReportChecksumMismatchError("Report file checksum mismatch")
        yield path
    except Exception:
        path.unlink(missing_ok=True)
        raise
    else:
        path.unlink(missing_ok=True)

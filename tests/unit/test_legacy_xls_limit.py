from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.etl.storage import read_report_file
from app.etl.worker_shutdown import LEGACY_XLS_TOO_LARGE_MESSAGE, LegacyReportTooLargeError


def test_legacy_xls_rejects_oversized_file(monkeypatch: pytest.MonkeyPatch) -> None:
    storage = MagicMock()

    def read_all(storage_uri: str, *, max_bytes: int) -> bytes:  # noqa: ARG001
        raise ValueError(f"File exceeds max allowed size ({max_bytes} bytes)")

    storage.read_all = read_all
    monkeypatch.setattr("app.etl.storage.get_report_storage", lambda: storage)

    with pytest.raises(LegacyReportTooLargeError, match=LEGACY_XLS_TOO_LARGE_MESSAGE):
        read_report_file("bucket/file.xls", filename="report.xls")

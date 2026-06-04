import re

from app.storage.supabase_storage import (
    SupabaseReportStorage,
    is_ascii_storage_key,
    storage_object_name,
)

_ALLOWED = re.compile(r"^[A-Za-z0-9._-]+$")


def test_storage_object_name_uses_report_id_and_extension() -> None:
    report_id = "70ea8033-6ae7-49b8-89b3-b28a6fd31677"
    filename = "Еженедельный детализированный отчет №736157629_284790 - 1.xlsx"
    assert storage_object_name(filename, report_id) == f"{report_id}.xlsx"


def test_storage_object_name_unknown_extension_falls_back_to_bin() -> None:
    report_id = "abc-123"
    assert storage_object_name("report.dat", report_id) == f"{report_id}.bin"


def test_object_path_has_no_forbidden_characters() -> None:
    storage = SupabaseReportStorage()
    user_id = "caefecb3-5789-4878-a9d4-929be573fbcc"
    report_id = "70ea8033-6ae7-49b8-89b3-b28a6fd31677"
    filename = "Еженедельный детализированный отчет №736157629_284790 - 1.xlsx"

    _bucket, path = storage._object_path(user_id, report_id, filename)

    assert path == f"{user_id}/{report_id}/{report_id}.xlsx"
    assert is_ascii_storage_key(path)
    for part in path.split("/"):
        assert _ALLOWED.match(part), f"invalid segment: {part!r}"

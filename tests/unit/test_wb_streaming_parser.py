from pathlib import Path

import pytest

from app.parsers.wb.streaming import iter_wb_normalized_rows

LARGE_FIXTURE = Path(__file__).resolve().parents[1] / "large_wb_report.xlsx"


@pytest.mark.skipif(not LARGE_FIXTURE.is_file(), reason="large_wb_report.xlsx not present")
def test_streaming_row_count_matches_baseline() -> None:
    total = 0
    parser_name = ""
    for parser, chunk in iter_wb_normalized_rows(
        LARGE_FIXTURE,
        filename=LARGE_FIXTURE.name,
        chunk_size=1000,
    ):
        parser_name = parser.name
        total += len(chunk)
    assert parser_name
    assert total == 22777

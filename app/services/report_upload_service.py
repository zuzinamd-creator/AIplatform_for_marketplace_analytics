"""Report upload validation — API-facing facade over ETL loaders (no API → ETL imports)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.etl.loaders import load_file_to_dataframe
from app.etl.storage import save_report_file
from app.etl.validators import validate_dataframe_values
from app.models.report import Marketplace

if TYPE_CHECKING:
    from collections.abc import Iterator


def validate_report_file(
    filename: str,
    content: bytes,
    *,
    marketplace: Marketplace,
) -> None:
    """Parse and validate upload bytes; raises ValueError on failure."""
    lower = filename.lower()
    df = load_file_to_dataframe(filename, content)

    if marketplace == Marketplace.WILDBERRIES and lower.endswith((".xlsx", ".xls", ".csv")):
        from app.parsers.wb import parse_wb_report

        try:
            _, rows = parse_wb_report(df)
        except Exception as exc:
            raise ValueError(
                "[wb_excel_unrecognized] Формат отчёта Wildberries не распознан. "
                "Загрузите еженедельный детализированный отчёт реализации (WB .xlsx)."
            ) from exc
        if not rows:
            raise ValueError(
                "[wb_no_data_rows] Report file contains no data rows. "
                "Проверьте, что выбран детализированный отчёт реализации с данными."
            )
        return

    try:
        validate_dataframe_values(df)
    except ValueError as exc:
        raise ValueError(
            "[invalid_values] Файл распознан, но содержит некорректные значения (числа/количества). "
            "Проверьте проблемные столбцы и повторите загрузку. "
            f"Детали: {str(exc)}"
        ) from exc


def persist_report_file(
    user_id: str,
    report_id: str,
    filename: str,
    chunks: Iterator[bytes],
) -> str:
    """Store report bytes; returns storage path."""
    return save_report_file(user_id, report_id, filename, chunks)

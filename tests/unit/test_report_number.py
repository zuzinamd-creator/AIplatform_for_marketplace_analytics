from app.domain.reports.report_number import extract_report_number
from app.models.report import Marketplace


def test_extract_wb_report_number_from_filename() -> None:
    num = extract_report_number(
        filename="Еженедельный детализированный отчет №726626521_284790 - 1.xlsx",
        marketplace=Marketplace.WILDBERRIES,
    )
    assert num == "726626521"


def test_extract_report_number_missing() -> None:
    assert (
        extract_report_number(
            filename="Еженедельный детализированный отчет WB.xlsx",
            marketplace=Marketplace.WILDBERRIES,
        )
        is None
    )

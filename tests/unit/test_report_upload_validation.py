"""Upload validation — WB Excel uses dedicated parser, not generic column rules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
from app.models.report import Marketplace
from app.services.report_upload_service import validate_report_file


def test_wb_xlsx_skips_generic_financial_column_validation() -> None:
    df = pd.DataFrame({"Кол-во": [0], "Выручка": [0]})
    with patch("app.services.report_upload_service.load_file_to_dataframe", return_value=df):
        with patch("app.parsers.wb.parse_wb_report", return_value=(MagicMock(), [])):
            validate_report_file("report.xlsx", b"fake", marketplace=Marketplace.WILDBERRIES)


def test_csv_still_uses_generic_validation() -> None:
    df = pd.DataFrame({"name": ["a"]})
    with patch("app.services.report_upload_service.load_file_to_dataframe", return_value=df):
        with patch("app.services.report_upload_service.validate_dataframe_values") as mock_val:
            validate_report_file("report.csv", b"a,b\n1", marketplace=Marketplace.WILDBERRIES)
            mock_val.assert_called_once_with(df)

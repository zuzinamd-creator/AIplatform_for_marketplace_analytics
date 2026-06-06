"""Upload validation — WB Excel uses dedicated parser, not generic column rules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from app.models.report import Marketplace
from app.services.report_upload_service import validate_report_file


def test_wb_xlsx_requires_parsed_rows() -> None:
    df = pd.DataFrame({"Кол-во": [0], "Выручка": [0]})
    with patch("app.services.report_upload_service.load_file_to_dataframe", return_value=df):
        with patch("app.parsers.wb.parse_wb_report", return_value=(MagicMock(), [])):
            with pytest.raises(ValueError, match="no data rows"):
                validate_report_file("report.xlsx", b"fake", marketplace=Marketplace.WILDBERRIES)


def test_wb_xlsx_accepts_non_empty_parsed_rows() -> None:
    df = pd.DataFrame({"Кол-во": [1], "Выручка": [100]})
    with patch("app.services.report_upload_service.load_file_to_dataframe", return_value=df):
        with patch("app.parsers.wb.parse_wb_report", return_value=(MagicMock(), [MagicMock()])):
            validate_report_file("report.xlsx", b"fake", marketplace=Marketplace.WILDBERRIES)


def test_csv_wb_uses_dedicated_parser() -> None:
    df = pd.DataFrame({"name": ["a"]})
    with patch("app.services.report_upload_service.load_file_to_dataframe", return_value=df):
        with patch("app.parsers.wb.parse_wb_report", return_value=(MagicMock(), [MagicMock()])) as mock_parse:
            validate_report_file("report.csv", b"a,b\n1", marketplace=Marketplace.WILDBERRIES)
            mock_parse.assert_called_once_with(df)

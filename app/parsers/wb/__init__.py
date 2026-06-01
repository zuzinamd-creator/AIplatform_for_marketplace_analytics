from __future__ import annotations

import pandas as pd

from app.parsers.wb.base import NormalizedWbRow, WbReportParserStrategy
from app.parsers.wb.strategies.realization_v1 import RealizationV1Parser
from app.parsers.wb.strategies.realization_v2 import RealizationV2Parser

STRATEGIES: tuple[type[WbReportParserStrategy], ...] = (
    RealizationV2Parser,
    RealizationV1Parser,
)


def select_wb_parser(df: pd.DataFrame) -> WbReportParserStrategy:
    for strategy_cls in STRATEGIES:
        if strategy_cls.supports(df):
            return strategy_cls()
    return RealizationV1Parser()


def parse_wb_report(df: pd.DataFrame) -> tuple[WbReportParserStrategy, list[NormalizedWbRow]]:
    parser = select_wb_parser(df)
    return parser, parser.parse(df)

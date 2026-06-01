from __future__ import annotations

import pandas as pd
from app.parsers.wb.base import WbReportParserStrategy, normalize_header, resolve_column_map
from app.parsers.wb.mapping import PARSER_VERSION_V1_SIGNATURE


class RealizationV1Parser(WbReportParserStrategy):
    name = "wb_realization"
    version = "v1"

    @classmethod
    def supports(cls, df: pd.DataFrame) -> bool:
        headers = {normalize_header(column) for column in df.columns}
        return len(PARSER_VERSION_V1_SIGNATURE.intersection(headers)) >= 2

    def parse(self, df: pd.DataFrame) -> list:
        column_map = resolve_column_map([str(c) for c in df.columns])
        rows = []
        for index, row in df.iterrows():
            rows.append(self._row_to_normalized(index=int(index), row=row, column_map=column_map))
        return rows

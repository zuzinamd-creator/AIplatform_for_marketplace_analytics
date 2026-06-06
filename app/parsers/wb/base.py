from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from app.parsers.wb.mapping import CANONICAL_FIELDS, FIELD_ALIASES


@dataclass(frozen=True)
class NormalizedWbRow:
    source_row_id: str
    source_row_index: int
    operation_date: date | None
    sku: str | None
    nm_id: str | None
    canonical: dict[str, object]
    raw: dict[str, str]


def normalize_header(value: object) -> str:
    return str(value).strip().lower().replace("\xa0", " ")


def _column_match_score(field: str, column: str) -> int:
    column_norm = normalize_header(column)
    if not column_norm:
        return 0
    best = 0
    for alias in FIELD_ALIASES.get(field, ()):
        alias_norm = normalize_header(alias)
        if column_norm == alias_norm:
            best = max(best, 200 + len(alias_norm))
            continue
        if alias_norm in column_norm:
            score = 100 + len(alias_norm)
            if field == "operation_date":
                if "заказ" in column_norm and "продаж" not in column_norm:
                    score -= 120
                if "фиксац" in column_norm:
                    score -= 80
                if "продаж" in column_norm:
                    score += 40
                if "операц" in column_norm:
                    score += 30
            if field == "sale_date":
                if "продаж" in column_norm:
                    score += 80
                if "заказ" in column_norm or "операц" in column_norm:
                    score -= 200
            if field == "retail_amount":
                if "скид" in column_norm or "withdisc" in column_norm or "disc" in column_norm:
                    score -= 60
                if "рознич" in column_norm or "retail" in column_norm:
                    score += 30
            best = max(best, score)
    return best


def resolve_column_map(columns: list[str]) -> dict[str, str | None]:
    resolved: dict[str, str | None] = {}
    for field in CANONICAL_FIELDS:
        best_score = 0
        best_column: str | None = None
        for column in columns:
            score = _column_match_score(field, column)
            if score > best_score:
                best_score = score
                best_column = column
        resolved[field] = best_column if best_score > 0 else None
    return resolved


def parse_decimal(value: object) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except Exception:
        return None


def parse_date(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    result = parsed.date()
    return result if isinstance(result, date) else None


class WbReportParserStrategy(ABC):
    name: str
    version: str

    @classmethod
    def supports(cls, df: pd.DataFrame) -> bool:
        return False

    @abstractmethod
    def parse(self, df: pd.DataFrame) -> list[NormalizedWbRow]:
        raise NotImplementedError

    def _row_to_normalized(
        self,
        *,
        index: int,
        row: pd.Series,
        column_map: dict[str, str | None],
    ) -> NormalizedWbRow:
        raw = {str(k): "" if pd.isna(v) else str(v) for k, v in row.items()}
        canonical: dict[str, Any] = {}
        for field, column in column_map.items():
            if column is None:
                canonical[field] = None
                continue
            value = row.get(column)
            if field == "operation_date":
                canonical[field] = parse_date(value)
            elif field == "sale_date":
                canonical[field] = parse_date(value)
            elif field == "quantity":
                dec = parse_decimal(value)
                canonical[field] = int(dec) if dec is not None else None
            elif field in {"sku", "nm_id", "warehouse_name", "operation_type"}:
                canonical[field] = None if pd.isna(value) else str(value).strip()
            elif field in CANONICAL_FIELDS:
                canonical[field] = parse_decimal(value)
            else:
                canonical[field] = None if pd.isna(value) else str(value).strip()

        operation_date = canonical.get("operation_date")
        sku_val = canonical.get("sku")
        nm_val = canonical.get("nm_id")
        return NormalizedWbRow(
            source_row_id=f"row-{index}",
            source_row_index=index,
            operation_date=operation_date if isinstance(operation_date, date) else None,
            sku=str(sku_val) if sku_val else None,
            nm_id=str(nm_val) if nm_val else None,
            canonical=canonical,
            raw=raw,
        )

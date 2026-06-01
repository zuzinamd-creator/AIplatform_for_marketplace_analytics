from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
from pydantic import ValidationError

from app.schemas.etl import FinancialValue, QuantityValue

FINANCIAL_COLUMN_TOKENS = ("revenue", "profit", "cost", "margin", "выруч", "прибыл", "себестоим")
QUANTITY_COLUMN_TOKENS = ("qty", "quantity", "count", "orders", "units", "колич", "заказ", "штук")


def validate_dataframe_values(df: pd.DataFrame) -> None:
    """Validate known financial and quantity columns before raw data is accepted."""
    errors: list[str] = []

    for column in df.columns:
        column_name = str(column)
        normalized_name = column_name.lower().strip()
        values = df[column].dropna()

        if _is_financial_column(normalized_name):
            errors.extend(_validate_financial_column(column_name, values))
        elif _is_quantity_column(normalized_name):
            errors.extend(_validate_quantity_column(column_name, values))

    if errors:
        raise ValueError("; ".join(errors[:20]))


def _is_financial_column(column_name: str) -> bool:
    return any(token in column_name for token in FINANCIAL_COLUMN_TOKENS)


def _is_quantity_column(column_name: str) -> bool:
    return any(token in column_name for token in QUANTITY_COLUMN_TOKENS)


def _validate_financial_column(column_name: str, values: pd.Series) -> list[str]:
    errors: list[str] = []
    for row_number, value in values.items():
        decimal_value = _to_decimal(value)
        if decimal_value is None:
            errors.append(f"{column_name}[row={row_number}] must be a valid Decimal")
            continue
        try:
            FinancialValue.model_validate({"value": decimal_value})
        except ValidationError:
            errors.append(f"{column_name}[row={row_number}] must be greater than 0")
    return errors


def _validate_quantity_column(column_name: str, values: pd.Series) -> list[str]:
    errors: list[str] = []
    for row_number, value in values.items():
        int_value = _to_int(value)
        if int_value is None:
            errors.append(f"{column_name}[row={row_number}] must be a non-negative integer")
            continue
        try:
            QuantityValue.model_validate({"value": int_value})
        except ValidationError:
            errors.append(f"{column_name}[row={row_number}] must be greater than or equal to 0")
    return errors


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).replace(",", ".").strip())
    except (InvalidOperation, AttributeError):
        return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        decimal_value = Decimal(str(value).replace(",", ".").strip())
    except (InvalidOperation, AttributeError):
        return None
    if decimal_value != decimal_value.to_integral_value():
        return None
    return int(decimal_value)

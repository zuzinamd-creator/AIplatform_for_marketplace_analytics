from __future__ import annotations

from datetime import date
from decimal import Decimal


def json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def serialize_payload(payload: dict) -> dict:
    return {str(key): json_safe(val) for key, val in payload.items()}

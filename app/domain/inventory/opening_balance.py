from __future__ import annotations

from datetime import date

from app.domain.inventory.errors import OpeningBalanceIntegrityError

OPENING_BALANCE_FLAG = "is_opening_balance"
OPENING_EFFECTIVE_DATE_FIELD = "opening_effective_date"


def is_opening_balance_movement(canonical_payload: dict[str, object]) -> bool:
    flag = canonical_payload.get(OPENING_BALANCE_FLAG)
    return flag is True or flag == "true" or flag == "1"


def _parse_date_value(raw: object) -> date | None:
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        return date.fromisoformat(raw.strip())
    return None


def opening_effective_date(
    canonical_payload: dict[str, object],
    *,
    fallback: date,
) -> date:
    """Resolve opening effective date from payload; never auto-shifts on conflict."""
    parsed = _parse_date_value(canonical_payload.get(OPENING_EFFECTIVE_DATE_FIELD))
    if parsed is not None:
        return parsed
    return fallback


def earliest_first_ledger_date(
    persisted_first_date: date | None,
    batch_first_date: date | None,
) -> date | None:
    """Earliest operation date from DB history and the current import batch."""
    if persisted_first_date is None:
        return batch_first_date
    if batch_first_date is None:
        return persisted_first_date
    return min(persisted_first_date, batch_first_date)


def validate_opening_balance_integrity(
    *,
    opening_date: date,
    sku: str | None,
    warehouse_name: str | None,
    first_ledger_operation_date: date | None,
) -> None:
    """
    Opening balance effective date must be strictly before the first ledger movement
    for the same tenant SKU / warehouse dimensions.

    No silent correction or auto-shifting.
    """
    if not sku:
        raise OpeningBalanceIntegrityError(
            "Opening balance requires a non-empty sku for integrity validation"
        )
    if first_ledger_operation_date is None:
        return
    if opening_date >= first_ledger_operation_date:
        raise OpeningBalanceIntegrityError(
            "Opening balance date "
            f"{opening_date.isoformat()} must be earlier than first ledger operation "
            f"{first_ledger_operation_date.isoformat()} for sku={sku!r} "
            f"warehouse={warehouse_name!r}"
        )

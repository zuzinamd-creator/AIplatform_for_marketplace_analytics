"""Opening balance integrity: effective date must precede first ledger movement."""

from datetime import date

import pytest
from app.domain.inventory.errors import OpeningBalanceIntegrityError
from app.domain.inventory.opening_balance import (
    earliest_first_ledger_date,
    is_opening_balance_movement,
    opening_effective_date,
    validate_opening_balance_integrity,
)


def test_valid_opening_balance_before_ledger() -> None:
    validate_opening_balance_integrity(
        opening_date=date(2026, 1, 1),
        sku="SKU-A",
        warehouse_name="WH-1",
        first_ledger_operation_date=date(2026, 1, 5),
    )


def test_overlap_with_existing_ledger_raises() -> None:
    with pytest.raises(OpeningBalanceIntegrityError, match="must be earlier"):
        validate_opening_balance_integrity(
            opening_date=date(2026, 1, 10),
            sku="SKU-A",
            warehouse_name="WH-1",
            first_ledger_operation_date=date(2026, 1, 10),
        )


def test_opening_after_first_ledger_raises() -> None:
    with pytest.raises(OpeningBalanceIntegrityError):
        validate_opening_balance_integrity(
            opening_date=date(2026, 2, 15),
            sku="SKU-A",
            warehouse_name="WH-1",
            first_ledger_operation_date=date(2026, 2, 5),
        )


def test_empty_ledger_allows_opening() -> None:
    validate_opening_balance_integrity(
        opening_date=date(2026, 3, 1),
        sku="SKU-NEW",
        warehouse_name="WH-1",
        first_ledger_operation_date=None,
    )


def test_multiple_warehouses_isolated() -> None:
    validate_opening_balance_integrity(
        opening_date=date(2026, 1, 1),
        sku="SKU-A",
        warehouse_name="WH-1",
        first_ledger_operation_date=date(2026, 1, 8),
    )
    with pytest.raises(OpeningBalanceIntegrityError):
        validate_opening_balance_integrity(
            opening_date=date(2026, 1, 9),
            sku="SKU-A",
            warehouse_name="WH-2",
            first_ledger_operation_date=date(2026, 1, 5),
        )


def test_multiple_skus_isolated() -> None:
    validate_opening_balance_integrity(
        opening_date=date(2026, 1, 1),
        sku="SKU-1",
        warehouse_name="WH-1",
        first_ledger_operation_date=date(2026, 1, 6),
    )
    with pytest.raises(OpeningBalanceIntegrityError):
        validate_opening_balance_integrity(
            opening_date=date(2026, 1, 7),
            sku="SKU-2",
            warehouse_name="WH-1",
            first_ledger_operation_date=date(2026, 1, 4),
        )


def test_opening_effective_date_parsed_from_iso_string() -> None:
    payload = {"is_opening_balance": True, "opening_effective_date": "2026-01-03"}
    assert is_opening_balance_movement(payload)
    assert opening_effective_date(payload, fallback=date(2026, 1, 10)) == date(2026, 1, 3)


def test_earliest_first_ledger_date_merges_batch_and_db() -> None:
    assert earliest_first_ledger_date(date(2026, 1, 10), date(2026, 1, 5)) == date(2026, 1, 5)
    assert earliest_first_ledger_date(None, date(2026, 1, 7)) == date(2026, 1, 7)
    assert earliest_first_ledger_date(date(2026, 1, 4), None) == date(2026, 1, 4)


def test_missing_sku_raises() -> None:
    with pytest.raises(OpeningBalanceIntegrityError, match="sku"):
        validate_opening_balance_integrity(
            opening_date=date(2026, 1, 1),
            sku=None,
            warehouse_name="WH-1",
            first_ledger_operation_date=None,
        )

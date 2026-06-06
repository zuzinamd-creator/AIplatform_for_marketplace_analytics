from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft
from app.domain.finance.wb_row_semantics import (
    LOGISTICS_RAW_KEYS,
    WbFinanceRowKind,
    allows_commission,
    allows_compensation,
    allows_deduction,
    allows_logistics,
    allows_payout,
    allows_penalty,
    allows_retail_amount,
    allows_return_amount,
    allows_storage,
    classify_wb_finance_row,
)
from app.models.finance.enums import LedgerOperationType
from app.parsers.wb.base import NormalizedWbRow, parse_decimal


class LedgerBuilder:
    """Build financial ledger drafts from normalized WB rows."""

    @staticmethod
    def from_normalized_rows(rows: list[NormalizedWbRow], *, default_date: date) -> list[LedgerEntryDraft]:
        entries: list[LedgerEntryDraft] = []
        for row in rows:
            entries.extend(LedgerBuilder._entries_for_row(row, default_date=default_date))
        return entries

    @staticmethod
    def _entries_for_row(row: NormalizedWbRow, *, default_date: date) -> list[LedgerEntryDraft]:
        operation_date = row.operation_date or default_date
        canonical = row.canonical
        kind = classify_wb_finance_row(canonical.get("operation_type"))
        drafts: list[LedgerEntryDraft] = []
        quantity = LedgerBuilder._sale_quantity(canonical, kind)

        typed_amounts: list[tuple[LedgerOperationType, Decimal | None]] = []

        if allows_retail_amount(kind):
            typed_amounts.append(
                (LedgerOperationType.SALE, LedgerBuilder._as_positive(canonical.get("retail_amount")))
            )
        if allows_commission(kind):
            typed_amounts.append(
                (LedgerOperationType.COMMISSION, LedgerBuilder._as_negative(canonical.get("commission")))
            )
        if allows_logistics(kind):
            logistics = LedgerBuilder._resolve_logistics(canonical, row.raw)
            typed_amounts.append((LedgerOperationType.LOGISTICS, LedgerBuilder._as_negative(logistics)))
        if allows_storage(kind):
            typed_amounts.append(
                (LedgerOperationType.STORAGE_FEE, LedgerBuilder._as_negative(canonical.get("storage_fee")))
            )
        if allows_penalty(kind):
            typed_amounts.append(
                (LedgerOperationType.PENALTY, LedgerBuilder._as_negative(canonical.get("penalty")))
            )
        typed_amounts.append(
            (LedgerOperationType.ACQUIRING, LedgerBuilder._as_negative(canonical.get("acquiring")))
        )
        if allows_compensation(kind):
            typed_amounts.append(
                (LedgerOperationType.COMPENSATION, LedgerBuilder._as_positive(canonical.get("compensation")))
            )
        if allows_deduction(kind):
            typed_amounts.append(
                (LedgerOperationType.DEDUCTION, LedgerBuilder._as_negative(canonical.get("deduction")))
            )
        if allows_payout(kind):
            payout = canonical.get("payout")
            typed_amounts.append(
                (
                    LedgerOperationType.PAYOUT,
                    payout if isinstance(payout, Decimal) else None,
                )
            )
        typed_amounts.append(
            (LedgerOperationType.ADVERTISEMENT, LedgerBuilder._as_negative(canonical.get("advertisement")))
        )
        if allows_return_amount(kind):
            typed_amounts.append(
                (LedgerOperationType.RETURN, LedgerBuilder._as_negative(canonical.get("return_amount")))
            )

        if kind == WbFinanceRowKind.RETURN:
            explicit_return = canonical.get("return_amount")
            explicit_return_present = isinstance(explicit_return, Decimal) and explicit_return != Decimal("0")
            sale_amount = LedgerBuilder._as_positive(canonical.get("retail_amount"))
            if (not explicit_return_present) and sale_amount is not None:
                typed_amounts.append((LedgerOperationType.RETURN, -abs(sale_amount)))

        metadata = {"parser_row_index": str(row.source_row_index)}
        if quantity > 0 and kind == WbFinanceRowKind.SALE:
            metadata["quantity"] = str(quantity)

        for operation_type, amount in typed_amounts:
            if amount is None or amount == Decimal("0"):
                continue
            drafts.append(
                LedgerEntryDraft(
                    operation_date=operation_date,
                    sku=row.sku,
                    nm_id=row.nm_id,
                    operation_type=operation_type,
                    amount=amount,
                    currency="RUB",
                    source_row_id=f"{row.source_row_id}:{operation_type.value}",
                    entry_metadata=metadata if operation_type == LedgerOperationType.SALE else None,
                )
            )

        if not drafts and allows_payout(kind) and canonical.get("payout") is not None:
            payout = canonical["payout"]
            if isinstance(payout, Decimal) and payout != Decimal("0"):
                drafts.append(
                    LedgerEntryDraft(
                        operation_date=operation_date,
                        sku=row.sku,
                        nm_id=row.nm_id,
                        operation_type=LedgerOperationType.PAYOUT,
                        amount=payout,
                        currency="RUB",
                        source_row_id=f"{row.source_row_id}:payout",
                    )
                )
        return drafts

    @staticmethod
    def _sale_quantity(canonical: dict[str, object], kind: WbFinanceRowKind) -> int:
        if kind != WbFinanceRowKind.SALE:
            return 0
        raw_qty = canonical.get("quantity")
        if isinstance(raw_qty, int) and raw_qty > 0:
            return raw_qty
        if isinstance(raw_qty, Decimal) and raw_qty > 0:
            return int(raw_qty)
        return 1

    @staticmethod
    def _resolve_logistics(canonical: dict[str, object], raw: dict[str, str]) -> Decimal | None:
        direct = canonical.get("logistics")
        if isinstance(direct, Decimal) and direct != Decimal("0"):
            return direct
        for key in LOGISTICS_RAW_KEYS:
            if key in raw:
                parsed = parse_decimal(raw[key])
                if parsed is not None and parsed != Decimal("0"):
                    return parsed
            key_lower = key.lower()
            for raw_key, raw_val in raw.items():
                if key_lower in str(raw_key).lower():
                    parsed = parse_decimal(raw_val)
                    if parsed is not None and parsed != Decimal("0"):
                        return parsed
        return None

    @staticmethod
    def _as_positive(value: object) -> Decimal | None:
        if not isinstance(value, Decimal):
            return None
        return abs(value)

    @staticmethod
    def _as_negative(value: object) -> Decimal | None:
        if not isinstance(value, Decimal):
            return None
        if value == Decimal("0"):
            return None
        return -abs(value)

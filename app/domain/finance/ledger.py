from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft
from app.models.finance.enums import LedgerOperationType
from app.parsers.wb.base import NormalizedWbRow


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
        drafts: list[LedgerEntryDraft] = []

        typed_amounts: list[tuple[LedgerOperationType, Decimal | None]] = [
            (LedgerOperationType.SALE, LedgerBuilder._as_positive(canonical.get("retail_amount"))),
            (LedgerOperationType.COMMISSION, LedgerBuilder._as_negative(canonical.get("commission"))),
            (LedgerOperationType.LOGISTICS, LedgerBuilder._as_negative(canonical.get("logistics"))),
            (LedgerOperationType.STORAGE_FEE, LedgerBuilder._as_negative(canonical.get("storage_fee"))),
            (LedgerOperationType.PENALTY, LedgerBuilder._as_negative(canonical.get("penalty"))),
            (LedgerOperationType.ACQUIRING, LedgerBuilder._as_negative(canonical.get("acquiring"))),
            (LedgerOperationType.COMPENSATION, LedgerBuilder._as_positive(canonical.get("compensation"))),
            (LedgerOperationType.DEDUCTION, LedgerBuilder._as_negative(canonical.get("deduction"))),
            (
                LedgerOperationType.PAYOUT,
                payout if isinstance((payout := canonical.get("payout")), Decimal) else None,
            ),
            (LedgerOperationType.ADVERTISEMENT, LedgerBuilder._as_negative(canonical.get("advertisement"))),
            (LedgerOperationType.RETURN, LedgerBuilder._as_negative(canonical.get("return_amount"))),
        ]

        op_hint = str(canonical.get("operation_type") or "").lower()
        if "возврат" in op_hint or "return" in op_hint:
            # Avoid double-counting if the report already provided an explicit return amount.
            explicit_return = canonical.get("return_amount")
            explicit_return_present = isinstance(explicit_return, Decimal) and explicit_return != Decimal("0")
            sale_amount = LedgerBuilder._as_positive(canonical.get("retail_amount"))
            if (not explicit_return_present) and sale_amount is not None:
                typed_amounts.append((LedgerOperationType.RETURN, -abs(sale_amount)))

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
                    entry_metadata={"parser_row_index": str(row.source_row_index)},
                )
            )

        if not drafts and canonical.get("payout") is not None:
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

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft
from app.domain.finance.wb_row_semantics import (
    LOGISTICS_RAW_KEYS,
    WbFinanceRowKind,
    allows_commission,
    allows_deduction,
    allows_logistics,
    allows_loyalty_compensation,
    allows_payout,
    allows_penalty,
    allows_pic_compensation,
    allows_retail_amount,
    allows_return_wb,
    allows_storage,
    allows_voluntary_compensation,
    allows_wb_realized_amount,
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
        return_basis: str | None = None

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
        if allows_return_wb(kind):
            return_amount, return_basis = LedgerBuilder._resolve_wb_return(canonical)
            if return_amount is not None:
                typed_amounts.append((LedgerOperationType.RETURN, return_amount))

        sale_metadata = LedgerBuilder._build_sale_metadata(
            canonical=canonical,
            kind=kind,
            source_row_index=row.source_row_index,
            quantity=quantity,
        )
        return_metadata = LedgerBuilder._build_return_metadata(
            canonical=canonical,
            kind=kind,
            source_row_index=row.source_row_index,
            return_basis=return_basis,
        )

        for operation_type, amount in typed_amounts:
            if amount is None or amount == Decimal("0"):
                continue
            entry_metadata: dict[str, str] | None = None
            if operation_type == LedgerOperationType.SALE:
                entry_metadata = sale_metadata
            elif operation_type == LedgerOperationType.RETURN:
                entry_metadata = return_metadata
            drafts.append(
                LedgerEntryDraft(
                    operation_date=operation_date,
                    sku=row.sku,
                    nm_id=row.nm_id,
                    operation_type=operation_type,
                    amount=amount,
                    currency="RUB",
                    source_row_id=f"{row.source_row_id}:{operation_type.value}",
                    entry_metadata=entry_metadata,
                )
            )

        for amount, compensation_metadata in LedgerBuilder._compensation_entry_specs(canonical, kind):
            drafts.append(
                LedgerEntryDraft(
                    operation_date=operation_date,
                    sku=row.sku,
                    nm_id=row.nm_id,
                    operation_type=LedgerOperationType.COMPENSATION,
                    amount=amount,
                    currency="RUB",
                    source_row_id=(
                        f"{row.source_row_id}:compensation:{compensation_metadata['compensation_kind']}"
                    ),
                    entry_metadata=compensation_metadata,
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
    def _compensation_entry_specs(
        canonical: dict[str, object],
        kind: WbFinanceRowKind,
    ) -> list[tuple[Decimal, dict[str, str]]]:
        specs: list[tuple[Decimal, dict[str, str]]] = []

        if allows_pic_compensation(kind):
            pic = LedgerBuilder._as_positive(canonical.get("payment_integration_compensation"))
            if pic is not None:
                specs.append((pic, {"compensation_kind": "pic"}))

        if allows_loyalty_compensation(kind):
            loyalty = LedgerBuilder._as_positive(canonical.get("loyalty_compensation"))
            if loyalty is not None:
                specs.append((loyalty, {"compensation_kind": "loyalty"}))

        if allows_voluntary_compensation(kind):
            voluntary = LedgerBuilder._as_positive(canonical.get("voluntary_compensation"))
            if voluntary is not None:
                specs.append((voluntary, {"compensation_kind": "voluntary"}))
            else:
                payout = canonical.get("payout")
                if isinstance(payout, Decimal) and payout != Decimal("0"):
                    specs.append((abs(payout), {"compensation_kind": "voluntary"}))

        # Legacy generic compensation: only on COMPENSATION-kind rows. After C1 rehydrate,
        # typed row kinds carry dedicated fields; emitting legacy here avoids double-counting.
        if kind == WbFinanceRowKind.COMPENSATION:
            legacy = LedgerBuilder._as_positive(canonical.get("compensation"))
            if legacy is not None:
                specs.append((legacy, {"compensation_kind": "legacy"}))

        return specs

    @staticmethod
    def _resolve_wb_return(canonical: dict[str, object]) -> tuple[Decimal | None, str | None]:
        return_wb = LedgerBuilder._as_positive(canonical.get("return_wb"))
        if return_wb is not None:
            return -return_wb, "wb"
        wb_realized = LedgerBuilder._as_positive(canonical.get("wb_realized_amount"))
        if wb_realized is not None:
            return -wb_realized, "wb"
        retail = LedgerBuilder._as_positive(canonical.get("retail_amount"))
        if retail is not None:
            return -retail, "gmv"
        return None, None

    @staticmethod
    def _wb_realized_metadata_value(canonical: dict[str, object]) -> str | None:
        wb_realized = canonical.get("wb_realized_amount")
        if isinstance(wb_realized, Decimal) and wb_realized != Decimal("0"):
            return str(wb_realized)
        return None

    @staticmethod
    def _build_sale_metadata(
        *,
        canonical: dict[str, object],
        kind: WbFinanceRowKind,
        source_row_index: int,
        quantity: int,
    ) -> dict[str, str] | None:
        if kind != WbFinanceRowKind.SALE:
            return None
        metadata: dict[str, str] = {"parser_row_index": str(source_row_index)}
        if quantity > 0:
            metadata["quantity"] = str(quantity)
        if allows_wb_realized_amount(kind):
            wb_value = LedgerBuilder._wb_realized_metadata_value(canonical)
            if wb_value is not None:
                metadata["wb_realized_amount"] = wb_value
        return metadata

    @staticmethod
    def _build_return_metadata(
        *,
        canonical: dict[str, object],
        kind: WbFinanceRowKind,
        source_row_index: int,
        return_basis: str | None,
    ) -> dict[str, str] | None:
        if kind != WbFinanceRowKind.RETURN:
            return None
        metadata: dict[str, str] = {"parser_row_index": str(source_row_index)}
        if allows_wb_realized_amount(kind):
            wb_value = LedgerBuilder._wb_realized_metadata_value(canonical)
            if wb_value is not None:
                metadata["wb_realized_amount"] = wb_value
        if return_basis is not None:
            metadata["return_basis"] = return_basis
        return metadata

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

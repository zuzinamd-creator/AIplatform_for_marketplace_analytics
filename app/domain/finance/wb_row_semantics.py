"""Classify Wildberries finance report rows for ledger field extraction."""

from __future__ import annotations

from enum import Enum

from app.parsers.wb.operation_semantics import normalize_operation_label


class WbFinanceRowKind(str, Enum):
    SALE = "sale"
    RETURN = "return"
    LOGISTICS = "logistics"
    STORAGE = "storage"
    DEDUCTION = "deduction"
    COMPENSATION = "compensation"
    REIMBURSEMENT = "reimbursement"
    PVZ_REIMBURSEMENT = "pvz_reimbursement"
    OTHER = "other"


_LOGISTICS_ALIASES = (
    "логистик",
    "logistic",
    "доставк",
    "delivery",
)
_STORAGE_ALIASES = ("хранен", "storage")
_DEDUCTION_ALIASES = ("удержан", "deduction")
_COMPENSATION_ALIASES = ("компенсац", "compensation")
_REIMBURSEMENT_ALIASES = ("возмещение издержек", "reimbursement")
_PVZ_ALIASES = ("возмещение за выдачу", "пвз")
_RETURN_ALIASES = ("возврат", "return")
_SALE_ALIASES = ("продаж", "sale", "реализац", "выкуп")


def classify_wb_finance_row(operation_type: object) -> WbFinanceRowKind:
    label = normalize_operation_label(operation_type)
    if not label:
        return WbFinanceRowKind.OTHER

    if any(token in label for token in _PVZ_ALIASES):
        return WbFinanceRowKind.PVZ_REIMBURSEMENT
    if any(token in label for token in _REIMBURSEMENT_ALIASES):
        return WbFinanceRowKind.REIMBURSEMENT
    if any(token in label for token in _RETURN_ALIASES):
        return WbFinanceRowKind.RETURN
    if any(token in label for token in _SALE_ALIASES):
        return WbFinanceRowKind.SALE
    if any(token in label for token in _LOGISTICS_ALIASES):
        return WbFinanceRowKind.LOGISTICS
    if any(token in label for token in _STORAGE_ALIASES):
        return WbFinanceRowKind.STORAGE
    if any(token in label for token in _DEDUCTION_ALIASES):
        return WbFinanceRowKind.DEDUCTION
    if any(token in label for token in _COMPENSATION_ALIASES):
        return WbFinanceRowKind.COMPENSATION
    return WbFinanceRowKind.OTHER


def allows_commission(kind: WbFinanceRowKind) -> bool:
    """WB commission is attributable only to sale/return realization rows."""
    return kind in {WbFinanceRowKind.SALE, WbFinanceRowKind.RETURN}


def allows_payout(kind: WbFinanceRowKind) -> bool:
    return kind == WbFinanceRowKind.SALE


def allows_retail_amount(kind: WbFinanceRowKind) -> bool:
    return kind in {WbFinanceRowKind.SALE, WbFinanceRowKind.RETURN}


def allows_return_amount(kind: WbFinanceRowKind) -> bool:
    """Do not read return_amount on sale rows — WB maps unrelated PVZ columns there."""
    return kind == WbFinanceRowKind.RETURN


def allows_logistics(kind: WbFinanceRowKind) -> bool:
    return kind == WbFinanceRowKind.LOGISTICS


def allows_storage(kind: WbFinanceRowKind) -> bool:
    return kind == WbFinanceRowKind.STORAGE


def allows_compensation(kind: WbFinanceRowKind) -> bool:
    return kind in {
        WbFinanceRowKind.COMPENSATION,
        WbFinanceRowKind.REIMBURSEMENT,
        WbFinanceRowKind.PVZ_REIMBURSEMENT,
    }


def allows_deduction(kind: WbFinanceRowKind) -> bool:
    return kind == WbFinanceRowKind.DEDUCTION


def allows_penalty(kind: WbFinanceRowKind) -> bool:
    return kind in {WbFinanceRowKind.DEDUCTION, WbFinanceRowKind.OTHER}


LOGISTICS_RAW_KEYS = (
    "Услуги по доставке товара покупателю",
    "Стоимость логистики",
    "логистика",
    "logistics",
    "delivery_rub",
)

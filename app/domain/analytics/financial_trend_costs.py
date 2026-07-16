"""Daily finance-trend cost fields from ledger day sums (Phase 9.12-B1)."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.models.finance.enums import LedgerOperationType


def ledger_day_trend_amounts(
    led: Mapping[LedgerOperationType, Decimal],
) -> dict[str, Decimal]:
    """
    Map per-day ledger operation totals into FinancialTrendPoint money fields.

    Expense-like ops use abs(); payout and sales keep signed sums (existing contract).
    """

    def _abs(op: LedgerOperationType) -> Decimal:
        return abs(led.get(op, Decimal("0")))

    return {
        "sales_revenue": led.get(LedgerOperationType.SALE, Decimal("0")),
        "returns_amount": _abs(LedgerOperationType.RETURN),
        "payout": led.get(LedgerOperationType.PAYOUT, Decimal("0")),
        "logistics": _abs(LedgerOperationType.LOGISTICS),
        "advertisement": _abs(LedgerOperationType.ADVERTISEMENT),
        "commission": _abs(LedgerOperationType.COMMISSION),
        "storage_fee": _abs(LedgerOperationType.STORAGE_FEE),
        "penalties": _abs(LedgerOperationType.PENALTY),
        "deductions": _abs(LedgerOperationType.DEDUCTION),
        "acquiring": _abs(LedgerOperationType.ACQUIRING),
        "other": _abs(LedgerOperationType.OTHER),
    }


FINANCIAL_TREND_LEDGER_OPS: tuple[LedgerOperationType, ...] = (
    LedgerOperationType.SALE,
    LedgerOperationType.RETURN,
    LedgerOperationType.PAYOUT,
    LedgerOperationType.LOGISTICS,
    LedgerOperationType.ADVERTISEMENT,
    LedgerOperationType.COMMISSION,
    LedgerOperationType.STORAGE_FEE,
    LedgerOperationType.PENALTY,
    LedgerOperationType.DEDUCTION,
    LedgerOperationType.ACQUIRING,
    LedgerOperationType.OTHER,
)

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft
from app.models.finance.enums import LedgerOperationType


@dataclass(frozen=True)
class ReconciliationResult:
    gross_revenue: Decimal
    net_revenue: Decimal
    wb_commissions: Decimal
    logistics: Decimal
    deductions: Decimal
    returns_amount: Decimal
    expected_payout: Decimal
    actual_payout: Decimal
    difference: Decimal


class ReconciliationCalculator:
    """Deterministic payout reconciliation from ledger drafts."""

    @staticmethod
    def calculate(entries: list[LedgerEntryDraft]) -> ReconciliationResult:
        zero = Decimal("0")
        gross = zero
        commissions = zero
        logistics = zero
        deductions = zero
        returns_amount = zero
        compensation = zero
        payout_actual = zero

        for entry in entries:
            amount = entry.amount
            if entry.operation_type == LedgerOperationType.SALE:
                gross += amount
            elif entry.operation_type == LedgerOperationType.COMMISSION:
                commissions += abs(amount)
            elif entry.operation_type == LedgerOperationType.LOGISTICS:
                logistics += abs(amount)
            elif entry.operation_type in (
                LedgerOperationType.DEDUCTION,
                LedgerOperationType.PENALTY,
                LedgerOperationType.STORAGE_FEE,
                LedgerOperationType.ACQUIRING,
                LedgerOperationType.ADVERTISEMENT,
            ):
                deductions += abs(amount)
            elif entry.operation_type == LedgerOperationType.RETURN:
                returns_amount += abs(amount)
            elif entry.operation_type == LedgerOperationType.COMPENSATION:
                compensation += amount
            elif entry.operation_type == LedgerOperationType.PAYOUT:
                payout_actual += amount

        net = gross - commissions - logistics - deductions - returns_amount + compensation
        expected = net
        difference = payout_actual - expected
        return ReconciliationResult(
            gross_revenue=gross,
            net_revenue=net,
            wb_commissions=commissions,
            logistics=logistics,
            deductions=deductions,
            returns_amount=returns_amount,
            expected_payout=expected,
            actual_payout=payout_actual,
            difference=difference,
        )

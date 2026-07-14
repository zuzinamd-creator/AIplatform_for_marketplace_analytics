"""Report manual expenses API schema tests."""

from decimal import Decimal

from app.schemas.report import ReportManualExpensesUpdate


def test_report_manual_expenses_update_accepts_partial_fields() -> None:
    wb_only = ReportManualExpensesUpdate(promotion_expenses=Decimal("100"))
    assert wb_only.promotion_expenses == Decimal("100")
    assert wb_only.jam_subscription_expenses is None

    jam_only = ReportManualExpensesUpdate(jam_subscription_expenses=Decimal("50"))
    assert jam_only.jam_subscription_expenses == Decimal("50")
    assert jam_only.promotion_expenses is None


def test_report_manual_expenses_update_accepts_both_fields() -> None:
    payload = ReportManualExpensesUpdate(
        promotion_expenses=Decimal("100"),
        jam_subscription_expenses=Decimal("50"),
    )
    assert payload.promotion_expenses == Decimal("100")
    assert payload.jam_subscription_expenses == Decimal("50")

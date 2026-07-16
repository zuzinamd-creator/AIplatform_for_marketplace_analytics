"""Phase 9.12-B1 — FinancialTrendPoint cost expansion + aggregation mapping."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.analytics.financial_trend_costs import (
    FINANCIAL_TREND_LEDGER_OPS,
    ledger_day_trend_amounts,
)
from app.models.finance.enums import LedgerOperationType
from app.models.report import Marketplace
from app.schemas.analytics import (
    AnalyticsFreshnessMeta,
    FinancialTrendPoint,
    FinancialTrendsResponse,
)
from app.schemas.dashboard import DashboardSummaryResponse


def test_financial_trend_point_defaults_include_new_cost_fields() -> None:
    point = FinancialTrendPoint(date=date(2026, 7, 1))
    assert point.commission == Decimal("0")
    assert point.storage_fee == Decimal("0")
    assert point.penalties == Decimal("0")
    assert point.deductions == Decimal("0")
    assert point.acquiring == Decimal("0")
    assert point.other == Decimal("0")
    # Legacy fields preserved
    assert point.logistics == Decimal("0")
    assert point.advertisement == Decimal("0")
    assert point.payout == Decimal("0")
    assert point.returns_amount == Decimal("0")


def test_financial_trend_point_serialization_includes_new_fields() -> None:
    point = FinancialTrendPoint(
        date=date(2026, 7, 2),
        sales_revenue=Decimal("1000"),
        logistics=Decimal("10"),
        advertisement=Decimal("20"),
        payout=Decimal("500"),
        returns_amount=Decimal("30"),
        commission=Decimal("40"),
        storage_fee=Decimal("5"),
        penalties=Decimal("6"),
        deductions=Decimal("7"),
        acquiring=Decimal("8"),
        other=Decimal("9"),
        gross_profit=Decimal("100"),
        margin_pct=Decimal("10"),
    )
    payload = point.model_dump(mode="json")
    for key in (
        "commission",
        "storage_fee",
        "penalties",
        "deductions",
        "acquiring",
        "other",
        "logistics",
        "advertisement",
        "payout",
        "returns_amount",
    ):
        assert key in payload
    assert payload["commission"] == "40"
    assert payload["storage_fee"] == "5"
    assert payload["other"] == "9"


def test_ledger_day_trend_amounts_abs_expenses_and_keeps_payout_signed() -> None:
    led = {
        LedgerOperationType.SALE: Decimal("1000"),
        LedgerOperationType.RETURN: Decimal("-50"),
        LedgerOperationType.PAYOUT: Decimal("800"),
        LedgerOperationType.LOGISTICS: Decimal("-12"),
        LedgerOperationType.ADVERTISEMENT: Decimal("-15"),
        LedgerOperationType.COMMISSION: Decimal("-90"),
        LedgerOperationType.STORAGE_FEE: Decimal("-3"),
        LedgerOperationType.PENALTY: Decimal("-4"),
        LedgerOperationType.DEDUCTION: Decimal("-5"),
        LedgerOperationType.ACQUIRING: Decimal("-6"),
        LedgerOperationType.OTHER: Decimal("-7"),
    }
    amounts = ledger_day_trend_amounts(led)
    assert amounts["sales_revenue"] == Decimal("1000")
    assert amounts["returns_amount"] == Decimal("50")
    assert amounts["payout"] == Decimal("800")
    assert amounts["logistics"] == Decimal("12")
    assert amounts["advertisement"] == Decimal("15")
    assert amounts["commission"] == Decimal("90")
    assert amounts["storage_fee"] == Decimal("3")
    assert amounts["penalties"] == Decimal("4")
    assert amounts["deductions"] == Decimal("5")
    assert amounts["acquiring"] == Decimal("6")
    assert amounts["other"] == Decimal("7")


def test_ledger_day_trend_amounts_empty_day_zeros() -> None:
    amounts = ledger_day_trend_amounts({})
    assert all(v == Decimal("0") for v in amounts.values())


def test_financial_trend_ledger_ops_include_new_cost_types() -> None:
    for op in (
        LedgerOperationType.COMMISSION,
        LedgerOperationType.STORAGE_FEE,
        LedgerOperationType.PENALTY,
        LedgerOperationType.DEDUCTION,
        LedgerOperationType.ACQUIRING,
        LedgerOperationType.OTHER,
        LedgerOperationType.LOGISTICS,
        LedgerOperationType.ADVERTISEMENT,
    ):
        assert op in FINANCIAL_TREND_LEDGER_OPS


def test_financial_trends_response_roundtrip_with_new_fields() -> None:
    freshness = AnalyticsFreshnessMeta(
        generated_at=datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC),
        data_as_of=None,
        stale_data_warning=False,
        semantics_version="1.0",
    )
    resp = FinancialTrendsResponse(
        marketplace=Marketplace.WILDBERRIES,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 7),
        points=[
            FinancialTrendPoint(
                date=date(2026, 7, 1),
                commission=Decimal("11"),
                storage_fee=Decimal("2"),
                penalties=Decimal("1"),
                deductions=Decimal("3"),
                acquiring=Decimal("4"),
                other=Decimal("0"),
            )
        ],
        freshness=freshness,
        integrity=None,
    )
    again = FinancialTrendsResponse.model_validate_json(resp.model_dump_json())
    assert again.points[0].commission == Decimal("11")
    assert again.points[0].deductions == Decimal("3")


def test_dashboard_summary_schema_accepts_expanded_finance_trend_point() -> None:
    """Additive fields must not break nested finance_trend_daily contract."""
    trends = FinancialTrendsResponse(
        marketplace=Marketplace.WILDBERRIES,
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 2),
        points=[
            FinancialTrendPoint(
                date=date(2026, 7, 1),
                sales_revenue=Decimal("100"),
                logistics=Decimal("1"),
                advertisement=Decimal("2"),
                payout=Decimal("50"),
                returns_amount=Decimal("3"),
                commission=Decimal("4"),
                storage_fee=Decimal("5"),
                penalties=Decimal("6"),
                deductions=Decimal("7"),
                acquiring=Decimal("8"),
                other=Decimal("9"),
            )
        ],
        freshness=AnalyticsFreshnessMeta(
            generated_at=datetime(2026, 7, 16, 12, 0, 0, tzinfo=UTC),
        ),
        integrity=None,
    )
    assert trends.points[0].commission == Decimal("4")
    assert trends.points[0].other == Decimal("9")
    # Legacy construction still works (new fields default to 0)
    legacy = FinancialTrendPoint(
        date=date(2026, 7, 1),
        sales_revenue=Decimal("100"),
        logistics=Decimal("1"),
        advertisement=Decimal("2"),
        payout=Decimal("50"),
        returns_amount=Decimal("3"),
    )
    assert legacy.commission == Decimal("0")
    assert "finance_trend_daily" in DashboardSummaryResponse.model_fields

from decimal import Decimal

from app.domain.analytics.profit_trust import (
    apply_profit_trust_to_ai_metrics,
    apply_profit_trust_to_kpis,
    classify_profit_trust,
    compute_period_compare_delta_profit,
)
from app.dto.analytics_dto import TopSKUSummaryDTO


def test_classify_profit_trust() -> None:
    assert classify_profit_trust(Decimal("100")) == "full"
    assert classify_profit_trust(Decimal("80")) == "partial"
    assert classify_profit_trust(Decimal("50")) == "partial"
    assert classify_profit_trust(Decimal("1")) == "partial"
    assert classify_profit_trust(Decimal("0")) == "insufficient"
    assert classify_profit_trust(None) == "insufficient"


def test_apply_profit_trust_to_kpis() -> None:
    profit = Decimal("900")
    margin = Decimal("90")
    assert apply_profit_trust_to_kpis(trust="full", total_profit=profit, margin_pct=margin) == (profit, margin)
    assert apply_profit_trust_to_kpis(trust="partial", total_profit=profit, margin_pct=margin) == (profit, None)
    assert apply_profit_trust_to_kpis(trust="insufficient", total_profit=profit, margin_pct=margin) == (None, None)


def test_compute_period_compare_delta_profit() -> None:
    assert compute_period_compare_delta_profit(Decimal("200"), Decimal("150")) == Decimal("50")
    assert compute_period_compare_delta_profit(None, Decimal("150")) is None
    assert compute_period_compare_delta_profit(Decimal("200"), None) is None
    assert compute_period_compare_delta_profit(None, None) is None


def test_apply_profit_trust_to_ai_metrics() -> None:
    top = [
        TopSKUSummaryDTO(
            internal_sku="sku-a",
            revenue=Decimal("1000"),
            profit=Decimal("300"),
            units_sold=10,
        )
    ]
    profit, margin, gated = apply_profit_trust_to_ai_metrics(
        trust="insufficient",
        total_profit=Decimal("500"),
        margin_pct=Decimal("50"),
        top_skus=top,
    )
    assert profit is None
    assert margin is None
    assert gated[0].profit == Decimal("0")
    assert gated[0].revenue == Decimal("1000")

    profit, margin, gated = apply_profit_trust_to_ai_metrics(
        trust="full",
        total_profit=Decimal("500"),
        margin_pct=Decimal("50"),
        top_skus=top,
    )
    assert profit == Decimal("500")
    assert margin == Decimal("50")
    assert gated[0].profit == Decimal("300")

from decimal import Decimal

from app.domain.analytics.profit_trust import apply_profit_trust_to_kpis, classify_profit_trust


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

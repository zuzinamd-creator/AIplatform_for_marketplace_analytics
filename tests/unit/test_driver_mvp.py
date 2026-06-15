"""Unit tests for Release 6.8.2 MVP driver layer."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.ai.drivers.cards import build_driver_card
from app.ai.drivers.decision import data_first_override, select_simple_decision
from app.ai.drivers.playbook import (
    estimate_effect,
    is_pricing_action,
    playbook_action,
    playbook_checks,
)
from app.ai.drivers.sku_factors import (
    DominantFactor,
    FactorDeltas,
    detect_dominant_factor,
    dominant_from_static,
)
from app.ai.drivers.bundle import _cards_from_snapshot
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO


def _factors(**kwargs) -> FactorDeltas:
    defaults = dict(
        sku="SKU-A",
        commissions_delta=Decimal("12400"),
        logistics_delta=Decimal("500"),
        returns_delta=Decimal("200"),
        cogs_delta=Decimal("0"),
        price_a=Decimal("590"),
        price_b=Decimal("650"),
        price_delta=Decimal("-60"),
        units_delta=-5,
        profit_delta=Decimal("-15000"),
        revenue_delta=Decimal("-12000"),
    )
    defaults.update(kwargs)
    return FactorDeltas(**defaults)


def test_detect_dominant_factor_commission() -> None:
    dom = detect_dominant_factor(_factors())
    assert dom.driver_type == "commission"
    assert dom.confidence in ("confirmed", "probable")


def test_playbook_commission_has_checks_and_action() -> None:
    checks = playbook_checks("commission")
    assert len(checks) >= 2
    action = playbook_action("commission", "SKU-B", confidence="confirmed")
    assert "SKU-B" in action
    assert "СПП" in action or "цену" in action.lower()


def test_estimate_effect_returns_range() -> None:
    low, high = estimate_effect("commission", Decimal("10000"))
    assert low > 0
    assert high > low


def test_build_driver_card_structure() -> None:
    dom = DominantFactor(driver_type="commission", factor_delta=Decimal("12400"), confidence="confirmed")
    card = build_driver_card(sku="SKU-B", dominant=dom, factors=_factors(), rank=1, impact_share_pct=71.0)
    assert card["sku"] == "SKU-B"
    assert card["driver_type"] == "commission"
    assert card["checks"]
    assert card["action"]
    assert card["cause"]
    assert card["rank"] == 1
    assert card["impact_share_pct"] == 71.0


def test_select_simple_decision_picks_higher_effect() -> None:
    cards = [
        {
            "card_id": "driver:A:commission",
            "sku": "SKU-A",
            "driver_type": "commission",
            "cause_confidence": "confirmed",
            "effect_high_rub": 4000,
            "metric_value_rub": -50000,
            "action": "Action A",
            "rank": 1,
        },
        {
            "card_id": "driver:B:commission",
            "sku": "SKU-B",
            "driver_type": "commission",
            "cause_confidence": "confirmed",
            "effect_high_rub": 12000,
            "metric_value_rub": -15000,
            "action": "Action B",
            "rank": 2,
        },
    ]
    decision = select_simple_decision(cards)
    assert decision is not None
    assert decision["action"] == "Action B"
    assert decision["sku"] == "SKU-B"
    assert decision["mode"] == "single"


def test_data_first_blocks_low_cost_coverage() -> None:
    snap = {"cost_coverage_pct": "65", "compare_available": True}
    grounded = GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date(2026, 5, 1),
        source_period_end=date(2026, 5, 31),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
    )
    validated = ValidatedInsightDTO(
        title="t",
        summary="s",
        confidence=Decimal("0.8"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        semantics_version="1.0",
    )
    cards = [{"driver_type": "commission", "action": "Пересчитайте цену"}]
    override = data_first_override(snap=snap, grounded=grounded, validated=validated, cards=cards)
    assert override is not None
    assert override["mode"] == "data_first"
    assert override["blocked_reason"] == "cost_coverage"
    assert "себестоимость" in override["action"].lower()


def test_data_first_blocks_degraded() -> None:
    snap = {"cost_coverage_pct": "100", "compare_available": True}
    grounded = GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=None,
        source_period_end=None,
        degraded_mode=True,
        rebuild_pending_count=0,
        rebuild_running_count=1,
    )
    validated = ValidatedInsightDTO(
        title="t",
        summary="s",
        confidence=Decimal("0.8"),
        degraded_mode=True,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        semantics_version="1.0",
    )
    override = data_first_override(snap=snap, grounded=grounded, validated=validated, cards=[])
    assert override is not None
    assert override["blocked_reason"] == "degraded"


def test_cards_from_snapshot_logistics() -> None:
    snap = {
        "logistics_high_burden_skus": [
            {"sku": "j-22-017", "share_pct": "47.5", "amount": "2320"},
        ],
    }
    cards = _cards_from_snapshot(snap)
    assert len(cards) == 1
    assert cards[0]["sku"] == "j-22-017"
    assert cards[0]["driver_type"] == "logistics"


def test_is_pricing_action() -> None:
    assert is_pricing_action("commission")
    assert is_pricing_action("price")
    assert not is_pricing_action("logistics")


def test_dominant_from_static() -> None:
    dom = dominant_from_static(driver_type="returns", amount=Decimal("900"), share_pct=Decimal("12"))
    assert dom.driver_type == "returns"

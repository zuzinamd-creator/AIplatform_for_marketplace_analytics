"""Unit tests for inventory intelligence layer and analyst."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.analysts import build_analytical_package, run_domain_analysts
from app.ai.analysts.inventory import InventoryAnalyst
from app.ai.executive import ExecutiveIntelligenceAggregator
from app.ai.insights.priority_engine import StructuredInsight, priority_level_for_finding, pick_executive_lead
from app.domain.inventory.intelligence import (
    InventoryIntelligenceResult,
    InventorySkuSignal,
    _inventory_risk_level,
    inventory_intelligence_to_snapshot,
)
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO, ContextDTO, MetricsDTO


def _grounded(**snap) -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date(2026, 1, 1),
        source_period_end=date(2026, 1, 31),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
        metrics_snapshot=snap,
    )


def _insight() -> AIInsightInputDTO:
    return AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date.today(),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(
            sku_count=10,
            total_revenue=Decimal("500000"),
            total_profit=Decimal("100000"),
            margin=Decimal("0.2"),
        ),
    )


def test_inventory_risk_level_high_on_dead_stock() -> None:
    assert _inventory_risk_level(slow_count=1, dead_count=3, frozen_share=None, concentration=None) == "high"


def test_inventory_intelligence_snapshot_serialization() -> None:
    result = InventoryIntelligenceResult(
        inventory_signals_available=True,
        turnover_available=True,
        frozen_capital_available=True,
        snapshot_date=date(2026, 1, 31),
        total_skus=5,
        total_frozen_capital=Decimal("120000"),
        frozen_capital_share_pct=Decimal("24.0"),
        slow_mover_count=2,
        dead_stock_count=1,
        overstock_count=1,
        stock_concentration_top3_pct=Decimal("65.0"),
        inventory_risk_level="medium",
        slow_movers=(
            InventorySkuSignal("SKU-A", 50, Decimal("30000"), 35),
        ),
        dead_stock=(
            InventorySkuSignal("SKU-B", 20, Decimal("10000"), 70),
        ),
        top_frozen_capital=(
            InventorySkuSignal("SKU-A", 50, Decimal("30000"), 35, Decimal("25")),
        ),
    )
    snap = inventory_intelligence_to_snapshot(result)
    assert snap["turnover_available"] is True
    assert snap["frozen_capital_available"] is True
    assert snap["inventory_slow_mover_count"] == 2
    assert snap["inventory_dead_stock_count"] == 1
    assert len(snap["inventory_slow_movers"]) == 1


def test_inventory_analyst_dead_stock_finding() -> None:
    snap = {
        "inventory_signals_available": True,
        "turnover_available": True,
        "frozen_capital_available": True,
        "inventory_total_skus": 8,
        "inventory_slow_mover_count": 2,
        "inventory_dead_stock_count": 4,
        "inventory_overstock_count": 1,
        "inventory_risk_level": "high",
        "inventory_total_frozen_capital": "85000",
        "inventory_frozen_capital_share_pct": "17.0",
        "inventory_stock_concentration_top3_pct": "72.0",
        "inventory_dead_stock": [
            {"sku": "SKU-X", "stock_units": 30, "frozen_capital": "15000", "days_since_last_sale": 90},
        ],
        "inventory_slow_movers": [
            {"sku": "SKU-Y", "stock_units": 10, "frozen_capital": "5000", "days_since_last_sale": 45},
        ],
        "inventory_top_frozen_capital": [
            {"sku": "SKU-X", "stock_units": 30, "frozen_capital": "15000", "share_pct": "40"},
        ],
    }
    pkg = build_analytical_package(grounded=_grounded(**snap), insight=_insight())
    out = InventoryAnalyst().analyze(pkg)
    ids = {f.finding_id for f in out.findings}
    assert "inventory_dead_stock" in ids
    assert "inventory_risk_high" in ids
    assert "мёртв" in out.findings[0].statement.lower() or "dead" in out.findings[0].finding_id


def test_inventory_findings_priority_l1() -> None:
    assert priority_level_for_finding("inventory_dead_stock", "high") == 1
    assert priority_level_for_finding("inventory_frozen_capital", "medium") == 2
    assert priority_level_for_finding("inventory_frozen_capital", "high") == 1
    assert priority_level_for_finding("inventory_risk_high", "high") == 2
    assert priority_level_for_finding("inventory_healthy", "low") == 3
    assert priority_level_for_finding("sales_top_sku", "low") == 1


def test_revenue_protection_primary_over_inventory() -> None:
    items = [
        StructuredInsight(
            "inv:1",
            2,
            "Заморожено 43 666 ₽ в остатках на складе (8.4% выручки).",
            "Деньги заморожены в остатках.",
            0.87,
            "Ускорьте оборачиваемость.",
            "domain",
            finding_id="inventory_frozen_capital",
        ),
        StructuredInsight(
            "sales:1",
            1,
            "Leading SKU j-31-239 in governed top-SKU list.",
            "Лидер по выручке задаёт основной риск периода.",
            0.85,
            "Улучшите карточку лидера.",
            "domain",
            finding_id="sales_top_sku",
        ),
    ]
    lead = pick_executive_lead(items)
    assert lead[0].finding_id == "sales_top_sku"
    assert any(l.finding_id and l.finding_id.startswith("inventory_") for l in lead)


def test_inventory_in_executive_aggregation() -> None:
    snap = {
        "inventory_signals_available": True,
        "turnover_available": True,
        "frozen_capital_available": True,
        "inventory_total_skus": 5,
        "inventory_dead_stock_count": 2,
        "inventory_slow_mover_count": 1,
        "inventory_risk_level": "medium",
        "inventory_total_frozen_capital": "40000",
        "inventory_dead_stock": [
            {"sku": "SKU-Z", "stock_units": 5, "frozen_capital": "20000", "days_since_last_sale": 65},
        ],
    }
    pkg = build_analytical_package(grounded=_grounded(**snap), insight=_insight())
    outputs = run_domain_analysts(pkg)
    agg = ExecutiveIntelligenceAggregator().aggregate(outputs)
    inv_insights = [i for i in agg.prioritized_insights if i.analyst_id == "inventory_analyst"]
    assert inv_insights
    assert any("мёртв" in i.statement.lower() or "заморож" in i.statement.lower() for i in inv_insights)

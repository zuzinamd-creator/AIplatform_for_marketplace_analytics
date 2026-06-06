"""Scenario tests for domain-analyst recommendation rules (deterministic layer)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.analysts import build_analytical_package, run_domain_analysts
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO, AnomalyDTO, ContextDTO, MetricsDTO, TopSKUSummaryDTO


def _grounded() -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date(2026, 5, 1),
        source_period_end=date(2026, 5, 31),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
    )


def _insight(
    *,
    sku_count: int = 10,
    total_revenue: Decimal | None = Decimal("100000"),
    total_profit: Decimal | None = Decimal("20000"),
    margin: Decimal | None = Decimal("0.20"),
    top_skus_summary: list[TopSKUSummaryDTO] | None = None,
    anomalies: list[AnomalyDTO] | None = None,
) -> AIInsightInputDTO:
    return AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date(2026, 5, 31),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(
            sku_count=sku_count,
            total_revenue=total_revenue,
            total_profit=total_profit,
            margin=margin,
            top_skus_summary=top_skus_summary or [],
        ),
        anomalies=anomalies or [],
    )


def _finding_ids(insight: AIInsightInputDTO) -> set[str]:
    pkg = build_analytical_package(grounded=_grounded(), insight=insight)
    outputs = run_domain_analysts(pkg)
    return {f.finding_id for o in outputs for f in o.findings}


def test_scenario_unprofitable_sku_low_margin() -> None:
    """Negative profit is not in MetricsDTO; low margin (<15%) is the governed signal."""
    ids = _finding_ids(_insight(margin=Decimal("0.08"), total_profit=Decimal("0")))
    assert "sales_low_margin" in ids


def test_scenario_low_margin() -> None:
    ids = _finding_ids(_insight(margin=Decimal("0.10")))
    assert "sales_low_margin" in ids


def test_scenario_high_returns_surfaces_anomaly() -> None:
    ids = _finding_ids(
        _insight(
            anomalies=[
                AnomalyDTO(
                    type="data_quality",
                    severity="high",
                    confidence=Decimal("0.9"),
                    message="Return rate exceeds 15% for SKU j-24-018",
                )
            ]
        )
    )
    assert any(fid.startswith("anomaly_") for fid in ids)


def test_scenario_revenue_present_for_healthy_business() -> None:
    ids = _finding_ids(_insight())
    assert "sales_revenue_present" in ids


def test_scenario_insufficient_data_no_sales_rules() -> None:
    insight = AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date.today(),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(sku_count=0),
    )
    pkg = build_analytical_package(grounded=_grounded(), insight=insight)
    sales = next(o for o in run_domain_analysts(pkg) if o.analyst_id.value == "sales_analyst")
    assert sales.insufficient_data is True


def test_scenario_funnel_concentration() -> None:
    insight = _insight(
        total_revenue=Decimal("100000"),
        top_skus_summary=[
            TopSKUSummaryDTO(internal_sku="SKU-A", revenue=Decimal("70000"), units_sold=100),
            TopSKUSummaryDTO(internal_sku="SKU-B", revenue=Decimal("10000"), units_sold=20),
        ],
    )
    ids = _finding_ids(insight)
    assert "funnel_concentration" in ids


def test_scenario_high_logistics_no_dedicated_rule() -> None:
    """MVP gap: no domain-analyst rule for logistics share; only LLM narrative if triggered."""
    ids = _finding_ids(_insight())
    assert not any("logistics" in fid for fid in ids)


def test_scenario_high_commission_no_dedicated_rule() -> None:
    """MVP gap: commission spike is not a deterministic finding_id."""
    ids = _finding_ids(_insight())
    assert not any("commission" in fid for fid in ids)


def test_scenario_sales_drop_via_anomaly() -> None:
    """Sales drop is surfaced as data_quality anomaly until dedicated rule exists."""
    ids = _finding_ids(
        _insight(
            anomalies=[
                AnomalyDTO(
                    type="data_quality",
                    severity="high",
                    confidence=Decimal("0.85"),
                    message="Week-over-week revenue down 40% for top SKU",
                )
            ]
        )
    )
    assert any(fid.startswith("anomaly_") for fid in ids)

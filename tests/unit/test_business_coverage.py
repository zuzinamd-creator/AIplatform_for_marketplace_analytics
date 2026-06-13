"""Unit tests for Business Coverage Engine (Phase 6.2)."""

from __future__ import annotations

from app.ai.coverage.business_coverage import assess_business_coverage, coverage_to_dict


def test_business_coverage_partial_data() -> None:
    report = assess_business_coverage(
        {
            "total_revenue": "505245",
            "sku_count": 46,
            "return_rate_pct": "3.5",
            "logistics_share_pct": "12.0",
            "commission_share_pct": "18.0",
            "storage_share_pct": "1.2",
            "cost_coverage_pct": "100",
            "total_profit": "229830",
            "margin": "45.5",
            "ad_spend_available": False,
            "inventory_signals_available": False,
        },
        deep_insights=[
            "Выручка упала на 6.1%. Главный фактор — объём: -97 шт; средний чек вырос.",
        ],
    )
    d = coverage_to_dict(report)
    assert 36 <= d["business_coverage_score"] <= 44
    assert d["missing_data_score"] == round(100 - d["business_coverage_score"], 1)
    assert d["advertising_data_coverage"] is False
    assert d["advertising_warning"] is not None
    assert "Ограничения анализа" in d["analysis_limitations"]
    assert any(c["status"] == "unknown" for c in d["root_cause_confidence"] if "реклам" in c["cause"])
    assert d["executive_summary_v2"]["recommended_uploads"]


def test_business_coverage_with_ads() -> None:
    report = assess_business_coverage(
        {
            "total_revenue": "100000",
            "sku_count": 10,
            "ad_spend_available": True,
            "ad_spend_total": "5000",
            "logistics_share_pct": "10",
            "commission_share_pct": "15",
            "cost_coverage_pct": "100",
            "total_profit": "20000",
        }
    )
    assert report.advertising_data_coverage is True
    assert report.advertising_warning is None


def test_root_cause_confidence_volume() -> None:
    report = assess_business_coverage(
        {"total_revenue": "100000", "sku_count": 5, "ad_spend_available": False},
        deep_insights=["Главный фактор — объём: +50 шт"],
    )
    causes = {c["cause"]: c for c in report.root_cause_confidence}
    assert causes["снижение/рост объёма продаж"]["reason_confidence"] == 0.91
    assert causes["влияние рекламы"]["status"] == "unknown"

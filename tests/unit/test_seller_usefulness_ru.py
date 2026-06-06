"""Tests for Russian seller usefulness and data-gap advisor."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.ai.product.data_gap_advisor import build_data_gap_advice
from app.ai.product.seller_usefulness import build_seller_usefulness
from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


def _validated() -> ValidatedInsightDTO:
    return ValidatedInsightDTO(
        title="Анализ выручки",
        summary="Общий доход за период составил 505 245 ₽ с маржой 28%.",
        bullets=["Сверьте вклад топ-SKU перед изменением цен."],
        confidence=Decimal("0.84"),
        degraded_mode=False,
        stale_data_warning=False,
        evidence_complete=True,
        workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
        semantics_version="1.0",
    )


def _grounded() -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date(2026, 5, 1),
        source_period_end=date(2026, 5, 31),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
        metrics_snapshot={
            "report_id": "abc",
            "sku_count": 12,
            "total_revenue": "505245",
            "margin": "28",
        },
    )


def test_seller_usefulness_uses_russian_not_english_template() -> None:
    scored = ScoredRecommendationDTO(
        title="Анализ",
        summary="Общий доход 505 245 ₽",
        bullets=["Сверьте вклад топ-SKU перед изменением цен."],
        confidence=Decimal("0.84"),
        priority_score=Decimal("80"),
        revenue_opportunity_score=Decimal("50"),
    )
    u = build_seller_usefulness(
        scored=scored, validated=_validated(), grounded=_grounded(), flags=[]
    )
    assert "Revenue or margin" not in u.why_this_matters
    assert "топ-SKU" in u.why_this_matters or "505" in u.why_this_matters
    assert u.urgency in ("сегодня", "на этой неделе", "когда будет время")
    assert u.data_gaps


def test_data_gap_advisor_skips_cost_import_when_margin_present() -> None:
    tips = build_data_gap_advice(
        sku_count=10,
        total_revenue=Decimal("500000"),
        margin=Decimal("43"),
        total_profit=Decimal("200000"),
    )
    assert not any("Импортируйте себестоимость" in t for t in tips)


def test_data_gap_advisor_suggests_cost_import() -> None:
    tips = build_data_gap_advice(sku_count=5, total_revenue=Decimal("1000"), cost_coverage_pct=40)
    assert any("себестоим" in t.lower() for t in tips)

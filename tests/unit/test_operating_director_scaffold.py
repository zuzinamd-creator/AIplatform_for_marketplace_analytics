"""Operating Director scaffold tests (Phase 6.3)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.ai.director.coverage_v2 import assess_coverage_v2
from app.ai.director.data_quality_auditor import run_data_quality_audit
from app.ai.director.dto import DomainExpertId
from app.ai.director.pipeline import run_operating_director, seller_report_text
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO, ContextDTO, MetricsDTO


def _snap() -> dict:
    return {
        "total_revenue": "505245",
        "sku_count": 46,
        "return_rate_pct": "3.5",
        "logistics_share_pct": "12",
        "commission_share_pct": "18",
        "storage_share_pct": "1.2",
        "cost_coverage_pct": "100",
        "total_profit": "229830",
        "margin": "45.5",
        "ad_spend_available": False,
        "inventory_signals_available": False,
        "deep_insights": [
            "Выручка упала на 6.1%. Главный фактор — объём: -97 шт.",
            "Высокая логистика на SKU j-24-018: 28% от выручки — рассмотрите упаковку.",
        ],
    }


def test_coverage_v2_lower_than_block_model() -> None:
    v2 = assess_coverage_v2(_snap())
    assert v2.coverage_score < Decimal("50")
    assert "Coverage V2" in v2.formula


def test_data_quality_auditor_blocks_ads_without_data() -> None:
    audit = run_data_quality_audit(_snap())
    assert DomainExpertId.SALES.value in audit.allowed_analysts
    assert DomainExpertId.ADVERTISING.value in audit.blocked_analysts
    assert DomainExpertId.TAX.value in audit.blocked_analysts
    assert audit.confidence_penalty > Decimal("0")


def test_operating_director_pipeline_produces_seller_report() -> None:
    grounded = GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date(2026, 5, 18),
        source_period_end=date(2026, 5, 24),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
        metrics_snapshot=_snap(),
    )
    insight = AIInsightInputDTO(
        context=ContextDTO(
            report_id=UUID("68e31bbd-4389-4c5c-bcae-0abdbfa47b89"),
            report_date=date(2026, 5, 24),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(
            sku_count=46,
            total_revenue=Decimal("505245"),
            total_profit=Decimal("229830"),
            margin=Decimal("45.5"),
        ),
    )
    trace = run_operating_director(grounded=grounded, insight_input=insight)
    assert trace.executive_report is not None
    text = seller_report_text(trace)
    assert "Главные выводы периода" in text
    assert "Ограничения анализа" in text
    assert trace.executive_report.top_actions
    for d in trace.domain_outputs:
        if d.ran:
            for f in d.findings:
                assert f.recommended_action
                assert f.root_cause

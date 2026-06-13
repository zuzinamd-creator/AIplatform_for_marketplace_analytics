"""Unit tests for Phase 6.2.2 insight engine."""

from __future__ import annotations

from decimal import Decimal

from app.ai.insights.composer import compose_insight_driven_output
from app.ai.insights.priority_engine import (
    StructuredInsight,
    collect_structured_insights,
    pick_executive_lead,
    priority_level_for_finding,
)
from app.ai.insights.quality import (
    StatementKind,
    classify_statement_kind,
    compute_insight_quality_score,
    detect_echo_pattern,
)
from app.ai.quality.recommendation_audit import (
    audit_insight_statements,
    is_dashboard_echo,
)
from app.dto.domain_analyst_dto import (
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


def test_classify_kpi_vs_insight_statement() -> None:
    assert classify_statement_kind("Общий доход за период составил 505 245 ₽") == StatementKind.KPI_STATEMENT
    assert (
        classify_statement_kind("Рост выручки обеспечен SKU X, который сформировал 42% прироста продаж.")
        == StatementKind.INSIGHT_STATEMENT
    )


def test_detect_echo_pattern_without_causal_analysis() -> None:
    echo = detect_echo_pattern("Общий доход за период составил 505 245 ₽", {"total_revenue": "505245"})
    assert echo.echo_detected is True
    assert echo.has_causal_analysis is False


def test_structured_insight_block_not_echo() -> None:
    text = (
        "Что произошло:\nВыручка выросла на 6.5%.\n\n"
        "Почему:\nОсновной вклад дал SKU X (+20 204 ₽).\n\n"
        "Действие:\nПроверить остатки SKU X."
    )
    assert is_dashboard_echo(text) is False


def test_priority_level_l1_for_revenue_drop() -> None:
    assert priority_level_for_finding("revenue_drop", "high") == 1
    assert priority_level_for_finding("sales_revenue_present", "info") == 3


def test_pick_executive_lead_prefers_level1() -> None:
    items = [
        StructuredInsight("a", 3, "Выручка составила 100 ₽", "x", 0.5, "act", "src"),
        StructuredInsight(
            "b",
            1,
            "Главный фактор — SKU-42",
            "драйвер периода по SKU",
            0.9,
            "act",
            "src",
            finding_id="revenue_sku_driver_x",
        ),
    ]
    lead = pick_executive_lead(items)
    assert len(lead) >= 1
    assert lead[0].insight_id == "b"


def test_insight_quality_score_components() -> None:
    score = compute_insight_quality_score(
        what_happened="Выручка выросла на 6.5%.",
        why="Основной вклад дал SKU X (+20 204 ₽).",
        action="Проверьте остатки и ценовую стратегию SKU X.",
        confidence=0.91,
        priority_level=1,
    )
    assert score.causal_depth >= 20.0
    assert score.business_relevance >= 20.0
    assert score.actionability >= 15.0
    assert score.overall >= 65.0


def test_collect_structured_insights_from_domain_analyst() -> None:
    finding = DomainFindingDTO(
        finding_id="revenue_drop",
        statement="Выручка упала на 12% относительно сравниваемого периода.",
        confidence=Decimal("0.88"),
        severity="high",
        evidence_refs=["kpi:revenue"],
        recommended_actions=["Проверьте топ-SKU с наибольшим падением."],
    )
    out = DomainAnalystOutputDTO(
        analyst_id=DomainAnalystId.REVENUE_CHANGE,
        contract_version="1.0",
        findings=[finding],
        overall_confidence=Decimal("0.88"),
    )
    items = collect_structured_insights(
        domain_outputs=[out],
        executive_insights=None,
        deep_bullets=None,
        causal_headline=None,
    )
    assert items
    assert items[0].priority_level == 1
    assert "Что произошло:" in items[0].format_block()


def test_compose_insight_driven_output_replaces_kpi_title() -> None:
    snap = {
        "deep_insights": [
            "Убыточный SKU WB-123 — маржа −8% после логистики.",
        ],
        "causal_headline": "Главный фактор периода — SKU WB-123 с просадкой маржи.",
    }
    out = compose_insight_driven_output(
        snap=snap,
        multi_trace=None,
        llm_title="Общий доход за период составил 505 245 ₽",
        llm_summary="Выручка за период составила 505 245 ₽ без детализации.",
    )
    assert "505 245" not in out.title
    assert out.insight_audit["echo_detected"] is False or out.title != "Общий доход за период составил 505 245 ₽"
    assert "Что произошло:" in out.executive_lead
    assert out.insight_quality["overall"] >= 50.0


def test_audit_insight_statements_rollup() -> None:
    audit = audit_insight_statements(
        title="Главный фактор — SKU X",
        summary="Что произошло:\nРост.\n\nПочему:\nSKU X.\n\nДействие:\nПроверьте цену.",
        structured_insights=[
            {
                "what_happened": "Рост выручки на 6%",
                "why": "SKU X дал основной вклад",
                "recommended_action": "Проверьте остатки SKU X",
                "insight_quality": {"overall": 78.0, "causal_depth": 20.0},
            }
        ],
        insight_quality={"overall": 80.0},
    )
    assert audit["insight_statement_count"] >= 1
    assert audit["insight_quality_avg"]["overall"] >= 70.0

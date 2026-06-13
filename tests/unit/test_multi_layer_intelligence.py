"""Unit tests for multi-layer domain analysts and executive aggregation."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.analysts import build_analytical_package, run_domain_analysts
from app.ai.evaluation.multi_layer_suite import run_multi_layer_eval_suite
from app.ai.executive import ExecutiveIntelligenceAggregator
from app.ai.prompts.contracts_v2 import PromptContractRegistryV2
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO, ContextDTO, MetricsDTO


def _insight() -> AIInsightInputDTO:
    return AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date.today(),
            marketplace_type="ozon",
        ),
        metrics=MetricsDTO(
            sku_count=5,
            total_revenue=Decimal("50000"),
            total_profit=Decimal("10000"),
            margin=Decimal("0.1"),
        ),
    )


def _grounded() -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
    )


def test_ten_domain_analysts_run() -> None:
    pkg = build_analytical_package(grounded=_grounded(), insight=_insight())
    outputs = run_domain_analysts(pkg)
    assert len(outputs) == 10
    assert all(o.advisory_only for o in outputs)


def test_sales_analyst_finds_low_margin() -> None:
    pkg = build_analytical_package(grounded=_grounded(), insight=_insight())
    sales = next(o for o in run_domain_analysts(pkg) if o.analyst_id.value == "sales_analyst")
    ids = {f.finding_id for f in sales.findings}
    assert "sales_low_margin" in ids


def test_executive_aggregation_narrative() -> None:
    pkg = build_analytical_package(grounded=_grounded(), insight=_insight())
    agg = ExecutiveIntelligenceAggregator().aggregate(run_domain_analysts(pkg))
    assert agg.narrative
    assert agg.prioritized_insights


def test_prompt_contracts_v2_registry() -> None:
    assert "analyst.sales.v2" in PromptContractRegistryV2.list_ids()


def test_multi_layer_eval_suite_all_pass() -> None:
    results = run_multi_layer_eval_suite()
    assert all(passed for _, passed in results), results

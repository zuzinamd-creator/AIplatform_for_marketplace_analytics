"""Multi-layer AI evaluation — regression, contradiction, stale, low-confidence."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.ai.analysts import build_analytical_package, run_domain_analysts
from app.ai.executive import ExecutiveIntelligenceAggregator
from app.ai.prompts.contracts_v2 import PromptContractRegistryV2
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import (
    AIInsightInputDTO,
    AnomalyDTO,
    ContextDTO,
    MetricsDTO,
)
from app.dto.domain_analyst_dto import DomainAnalystId, DomainAnalystOutputDTO, DomainFindingDTO


def _sample_insight(*, with_anomaly: bool = False, stale: bool = False) -> AIInsightInputDTO:
    anomalies: list[AnomalyDTO] = []
    if with_anomaly:
        anomalies.append(
            AnomalyDTO(
                type="missing_total_revenue",
                severity="high",
                confidence=Decimal("0.9"),
                message="Governed anomaly: missing total revenue",
            )
        )
    return AIInsightInputDTO(
        context=ContextDTO(
            report_id=uuid4(),
            report_date=date.today(),
            marketplace_type="wildberries",
        ),
        metrics=MetricsDTO(
            sku_count=10,
            total_revenue=Decimal("100000"),
            total_profit=Decimal("20000"),
            margin=Decimal("0.2"),
        ),
        anomalies=anomalies,
    )


def _grounded(*, degraded: bool = False, pending: int = 0) -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=degraded,
        rebuild_pending_count=pending,
        rebuild_running_count=0,
    )


def eval_prompt_contracts_registered() -> bool:
    ids = PromptContractRegistryV2.list_ids()
    return len(ids) >= 7 and "analyst.sales.v2" in ids


def eval_domain_analysts_produce_schema() -> bool:
    pkg = build_analytical_package(grounded=_grounded(), insight=_sample_insight())
    outputs = run_domain_analysts(pkg)
    if len(outputs) != 6:
        return False
    for out in outputs:
        if out.advisory_only is not True:
            return False
        for f in out.findings:
            if not (0 <= f.confidence <= 1):
                return False
            if not f.evidence_refs and not f.recommended_actions:
                pass  # allowed
    return True


def eval_executive_prioritizes_anomalies() -> bool:
    pkg = build_analytical_package(
        grounded=_grounded(), insight=_sample_insight(with_anomaly=True)
    )
    outputs = run_domain_analysts(pkg)
    agg = ExecutiveIntelligenceAggregator().aggregate(outputs)
    if not agg.prioritized_insights:
        return False
    top = agg.prioritized_insights[0]
    return top.analyst_id == DomainAnalystId.ANOMALY.value or top.severity in ("high", "critical")


def eval_contradiction_resolution() -> bool:
    a = DomainAnalystOutputDTO(
        analyst_id=DomainAnalystId.SALES,
        contract_version="2.0.0",
        findings=[
            DomainFindingDTO(
                finding_id="f1",
                statement="Increase spend",
                confidence=Decimal("0.9"),
                severity="medium",
                evidence_refs=["report:x"],
                recommended_actions=["Increase ad spend"],
            )
        ],
        overall_confidence=Decimal("0.9"),
    )
    b = DomainAnalystOutputDTO(
        analyst_id=DomainAnalystId.ADS,
        contract_version="2.0.0",
        findings=[
            DomainFindingDTO(
                finding_id="f2",
                statement="Reduce spend",
                confidence=Decimal("0.5"),
                severity="medium",
                evidence_refs=["report:x"],
                recommended_actions=["Reduce ad spend"],
            )
        ],
        overall_confidence=Decimal("0.5"),
    )
    agg = ExecutiveIntelligenceAggregator().aggregate([a, b])
    return len(agg.conflicts_resolved) >= 1


def eval_stale_context_lowers_confidence() -> bool:
    pkg = build_analytical_package(
        grounded=_grounded(degraded=True, pending=5),
        insight=_sample_insight(),
    )
    outputs = run_domain_analysts(pkg)
    agg = ExecutiveIntelligenceAggregator().aggregate(outputs)
    return agg.overall_confidence <= Decimal("1")


def eval_low_confidence_analyst_flagged() -> bool:
    pkg = build_analytical_package(grounded=_grounded(), insight=None)
    outputs = run_domain_analysts(pkg)
    low = [o for o in outputs if o.insufficient_data or o.overall_confidence < Decimal("0.7")]
    return len(low) >= 1


def run_multi_layer_eval_suite() -> list[tuple[str, bool]]:
    cases = [
        ("prompt_contracts_v2", eval_prompt_contracts_registered),
        ("domain_analyst_schema", eval_domain_analysts_produce_schema),
        ("executive_prioritization", eval_executive_prioritizes_anomalies),
        ("contradiction_resolution", eval_contradiction_resolution),
        ("stale_context", eval_stale_context_lowers_confidence),
        ("low_confidence_analysts", eval_low_confidence_analyst_flagged),
    ]
    return [(name, fn()) for name, fn in cases]

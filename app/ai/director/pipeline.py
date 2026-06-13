"""Operating Director pipeline — parallel scaffold to legacy AIIntelligenceEngine."""

from __future__ import annotations

from app.ai.director.cross_domain import run_cross_domain_analysts
from app.ai.director.data_quality_auditor import run_data_quality_audit
from app.ai.director.domain_experts import run_domain_experts
from app.ai.director.dto import OperatingDirectorTraceDTO
from app.ai.director.executive_director import build_executive_report, format_seller_report
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO


class OperatingDirectorPipeline:
    """Strangler-fig entrypoint: run alongside legacy engine, do not replace yet."""

    architecture_version = "operating_director_v1"

    def run(
        self,
        *,
        grounded: GroundedContextDTO,
        insight_input: AIInsightInputDTO | None,
    ) -> OperatingDirectorTraceDTO:
        snap = dict(grounded.metrics_snapshot or {})
        audit = run_data_quality_audit(snap)

        domain_outputs = run_domain_experts(
            audit=audit,
            grounded=grounded,
            insight_input=insight_input,
        )
        cross_outputs = run_cross_domain_analysts(domain_outputs)

        period_label = ""
        if grounded.source_period_start and grounded.source_period_end:
            period_label = f"{grounded.source_period_start} — {grounded.source_period_end}"

        executive = build_executive_report(
            audit=audit,
            domain_outputs=domain_outputs,
            cross_outputs=cross_outputs,
            period_label=period_label,
        )

        return OperatingDirectorTraceDTO(
            quality_audit=audit,
            domain_outputs=domain_outputs,
            cross_domain_outputs=cross_outputs,
            executive_report=executive,
        )


def run_operating_director(
    *,
    grounded: GroundedContextDTO,
    insight_input: AIInsightInputDTO | None,
) -> OperatingDirectorTraceDTO:
    return OperatingDirectorPipeline().run(grounded=grounded, insight_input=insight_input)


def seller_report_text(trace: OperatingDirectorTraceDTO) -> str:
    if trace.executive_report is None:
        return ""
    return format_seller_report(trace.executive_report)

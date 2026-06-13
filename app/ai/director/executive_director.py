"""Level 3 — Executive Director (seller report from analyst outputs only)."""

from __future__ import annotations

from decimal import Decimal

from app.ai.director.dto import (
    CrossDomainOutputDTO,
    DataQualityAuditDTO,
    DomainExpertOutputDTO,
    ExecutiveDirectorReportDTO,
)


def build_executive_report(
    *,
    audit: DataQualityAuditDTO,
    domain_outputs: list[DomainExpertOutputDTO],
    cross_outputs: list[CrossDomainOutputDTO],
    period_label: str = "",
) -> ExecutiveDirectorReportDTO:
    """Compose seller report WITHOUT reading raw KPI from metrics_snapshot."""
    all_actions: list[tuple[Decimal, str]] = []
    all_causes: list[str] = []
    all_risks: list[str] = []
    all_conclusions: list[tuple[Decimal, str]] = []

    for d in domain_outputs:
        if not d.ran:
            continue
        for f in d.findings:
            all_actions.append((f.confidence, f.recommended_action))
            all_causes.append(f.root_cause[:200])
            all_conclusions.append((f.confidence, f.finding[:200]))
            if f.severity in ("high", "critical"):
                all_risks.append(f.finding[:200])

    for c in cross_outputs:
        if not c.ran:
            continue
        for f in c.findings:
            all_actions.append((f.confidence, f.recommended_action))
            all_causes.append(f.root_cause[:200])
            all_conclusions.append((f.confidence, f.finding[:200]))
            if "risk" in f.finding_id or c.analyst_id.value == "risk_analyst":
                all_risks.append(f.finding[:200])

    all_actions.sort(key=lambda x: x[0], reverse=True)
    all_conclusions.sort(key=lambda x: x[0], reverse=True)

    limitations = _limitations_block(audit)

    confs = [d.overall_confidence for d in domain_outputs if d.ran and d.findings]
    confs += [c.overall_confidence for c in cross_outputs if c.ran and c.findings]
    overall = sum(confs) / Decimal(len(confs)) if confs else Decimal("0.4")
    overall *= Decimal("1") - audit.confidence_penalty

    return ExecutiveDirectorReportDTO(
        period_label=period_label,
        top_conclusions=[t for _, t in all_conclusions[:3]],
        main_causes=list(dict.fromkeys(all_causes))[:5],
        top_risks=list(dict.fromkeys(all_risks))[:3] or ["Явных критических рисков по доступным данным не выявлено."],
        top_actions=[a for _, a in all_actions[:3]],
        analysis_limitations=limitations,
        quality_audit=audit,
        confidence=min(Decimal("1"), max(Decimal("0"), overall)),
    )


def format_seller_report(report: ExecutiveDirectorReportDTO) -> str:
    lines = [
        "## Главные выводы периода",
        *[f"• {x}" for x in report.top_conclusions or ["—"]],
        "",
        "## Главные причины",
        *[f"• {x}" for x in report.main_causes or ["—"]],
        "",
        "## Главные риски",
        *[f"• {x}" for x in report.top_risks or ["—"]],
        "",
        "## Главные действия",
        *[f"{i + 1}. {x}" for i, x in enumerate(report.top_actions or ["—"])],
        "",
        report.analysis_limitations,
    ]
    return "\n".join(lines)


def _limitations_block(audit: DataQualityAuditDTO) -> str:
    missing = ", ".join(audit.missing_blocks[:8]) if audit.missing_blocks else "нет"
    blocked = ", ".join(audit.blocked_analysts[:6]) if audit.blocked_analysts else "нет"
    return (
        "## Ограничения анализа\n\n"
        f"Business Coverage V2: {audit.coverage_score}% ({audit.coverage_formula})\n\n"
        f"Неполные или отсутствующие блоки: {missing}.\n\n"
        f"Не запущены аналитики: {blocked}.\n\n"
        "Executive Director формирует отчёт только из выводов доступных аналитиков. "
        "При добавлении данных отчёт может существенно измениться."
    )

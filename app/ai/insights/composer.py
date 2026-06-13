"""Compose insight-driven titles and summaries (Phase 6.2.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ai.insights.priority_engine import (
    StructuredInsight,
    collect_structured_insights,
    pick_executive_lead,
)
from app.ai.insights.quality import (
    audit_text_fields,
    compute_insight_quality_score,
)
from app.dto.domain_analyst_dto import DomainAnalystOutputDTO, ExecutiveInsightDTO, MultiLayerReasoningTraceDTO


@dataclass(frozen=True)
class InsightDrivenOutput:
    title: str
    summary: str
    bullets: tuple[str, ...]
    executive_lead: str
    structured_insights: tuple[dict[str, Any], ...]
    insight_audit: dict[str, Any]
    insight_quality: dict[str, float]
    primary_insight: dict[str, Any] | None

    def to_snapshot_payload(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "executive_lead": self.executive_lead,
            "structured_insights": list(self.structured_insights),
            "insight_audit": self.insight_audit,
            "insight_quality": self.insight_quality,
            "primary_insight": self.primary_insight,
            "engine_version": "insight_v1",
        }


def compose_insight_driven_output(
    *,
    snap: dict,
    multi_trace: MultiLayerReasoningTraceDTO | None,
    llm_title: str,
    llm_summary: str,
) -> InsightDrivenOutput:
    domain_outputs = multi_trace.domain_outputs if multi_trace else []
    executive_insights = multi_trace.domain_insights if multi_trace else []
    deep = list(snap.get("deep_insights") or [])
    headline = snap.get("causal_headline")

    structured = collect_structured_insights(
        domain_outputs=domain_outputs,
        executive_insights=executive_insights,
        deep_bullets=deep,
        causal_headline=str(headline) if headline else None,
    )
    lead = pick_executive_lead(structured)

    if not lead and structured:
        lead = structured[:3]

    if not lead:
        lead = [
            StructuredInsight(
                insight_id="fallback:data_review",
                priority_level=2,
                what_happened="За период есть governed KPI, но causal-insights ограничены доступными данными.",
                why="Недостаточно сигналов уровня 1 для автоматического root cause.",
                confidence=0.6,
                recommended_action="Сверьте топ-SKU, возвраты и маржу на Dashboard, затем повторите анализ.",
                source="fallback",
            )
        ]

    primary = lead[0]
    blocks = [ins.format_block() for ins in lead[:3]]
    executive_lead = "\n\n---\n\n".join(blocks)
    summary = executive_lead
    title = primary.headline()

    bullets: list[str] = []
    for ins in lead[:5]:
        bullets.append(f"{ins.what_happened} → {ins.recommended_action}")
    for ins in structured[3:8]:
        if ins.insight_id not in {x.insight_id for x in lead[:5]}:
            bullets.append(ins.what_happened)

    quality = compute_insight_quality_score(
        what_happened=primary.what_happened,
        why=primary.why,
        action=primary.recommended_action,
        confidence=primary.confidence,
        priority_level=primary.priority_level,
    )

    structured_dicts = [_insight_dict(i, quality if i.insight_id == primary.insight_id else None) for i in structured[:8]]
    output_audit = audit_text_fields({"title": title, "summary": summary}, snap)
    llm_audit = audit_text_fields(
        {"llm_title": llm_title, "llm_summary": llm_summary[:400]},
        snap,
    )
    audit = {
        **output_audit,
        "echo_detected": output_audit["echo_detected"],
        "llm_echo_detected": llm_audit["echo_detected"],
        "llm_echo_fields": llm_audit.get("echo_fields") or [],
    }

    return InsightDrivenOutput(
        title=title[:255],
        summary=summary[:4000],
        bullets=tuple(bullets[:12]),
        executive_lead=executive_lead[:4000],
        structured_insights=tuple(structured_dicts),
        insight_audit=audit,
        insight_quality=quality.to_dict(),
        primary_insight=_insight_dict(primary, quality),
    )


def _insight_dict(ins: StructuredInsight, quality=None) -> dict[str, Any]:
    payload = {
        "insight_id": ins.insight_id,
        "priority_level": ins.priority_level,
        "what_happened": ins.what_happened,
        "why": ins.why,
        "confidence": ins.confidence,
        "recommended_action": ins.recommended_action,
        "source": ins.source,
        "finding_id": ins.finding_id,
    }
    if quality is not None:
        payload["insight_quality"] = quality.to_dict()
    return payload

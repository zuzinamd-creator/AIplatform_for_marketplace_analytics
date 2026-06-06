"""Grounded context assembly on top of AIExecutionContext."""

from __future__ import annotations

from app.ai.context import AIExecutionContext
from app.ai.grounding.retrieval import period_from_evidence, retrieve_evidence
from app.dto.ai_analytics_dto import GroundedContextDTO


def build_grounded_context(ctx: AIExecutionContext) -> GroundedContextDTO:
    evidence = retrieve_evidence(ctx.insight_input)
    period_start, period_end = period_from_evidence(evidence)
    metrics: dict = {}
    if ctx.insight_input is not None:
        metrics = ctx.insight_input.to_legacy_dict()
        metrics["anomaly_messages"] = [
            str(a.get("message", "")) for a in (metrics.get("anomalies") or [])
        ]
        metrics["inventory_signals_available"] = False
        metrics["ad_spend_available"] = False
        if ctx.governed_extras:
            metrics.update(ctx.governed_extras)

    freshness_parts: list[str] = []
    if ctx.rebuild_running_count > 0:
        freshness_parts.append("rebuild in progress")
    if ctx.rebuild_pending_count > 0:
        freshness_parts.append(f"{ctx.rebuild_pending_count} pending rebuild(s)")
    freshness = "; ".join(freshness_parts) if freshness_parts else "current"

    return GroundedContextDTO(
        semantics_version=ctx.semantics_version,
        data_as_of=ctx.data_as_of,
        source_period_start=period_start,
        source_period_end=period_end,
        degraded_mode=ctx.degraded_mode,
        rebuild_pending_count=ctx.rebuild_pending_count,
        rebuild_running_count=ctx.rebuild_running_count,
        evidence=evidence,
        metrics_snapshot=metrics,
        freshness_note=freshness,
    )

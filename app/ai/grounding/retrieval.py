"""Evidence retrieval from deterministic platform snapshots (no vector DB required)."""

from __future__ import annotations

from datetime import date

from app.dto.ai_analytics_dto import EvidenceRefDTO
from app.dto.analytics_dto import AIInsightInputDTO


def retrieve_evidence(
    insight: AIInsightInputDTO | None,
    *,
    report_id: str | None = None,
) -> tuple[EvidenceRefDTO, ...]:
    """Build evidence refs from typed insight input only."""
    if insight is None:
        return ()
    rid = str(insight.context.report_id) if report_id is None else report_id
    period = insight.context.report_date
    refs: list[EvidenceRefDTO] = [
        EvidenceRefDTO(
            source_type="report",
            source_id=rid,
            label="Primary report context",
            period_start=period,
            period_end=period,
        ),
    ]
    if insight.metrics.total_revenue is not None:
        refs.append(
            EvidenceRefDTO(
                source_type="aggregated_metrics",
                source_id=f"{rid}:revenue",
                label="Total revenue (deterministic DTO)",
                period_start=period,
                period_end=period,
            )
        )
    for anomaly in insight.anomalies:
        refs.append(
            EvidenceRefDTO(
                source_type="anomaly",
                source_id=f"{rid}:{anomaly.type}",
                label=anomaly.message[:200],
                period_start=period,
                period_end=period,
            )
        )
    return tuple(refs)


def period_from_evidence(evidence: tuple[EvidenceRefDTO, ...]) -> tuple[date | None, date | None]:
    starts = [e.period_start for e in evidence if e.period_start]
    ends = [e.period_end for e in evidence if e.period_end]
    if not starts:
        return None, None
    return min(starts), max(ends)

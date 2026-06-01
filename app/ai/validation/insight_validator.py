"""Insight validation — confidence, stale data, unsupported claims."""

from __future__ import annotations

import json
import re
from decimal import Decimal

from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO

_CURRENCY_CLAIM = re.compile(r"\b\d[\d\s,.]*\s*(?:₽|rub|руб)\b", re.I)


def validate_insight_output(
    *,
    workflow: AnalyticsWorkflow,
    grounded: GroundedContextDTO,
    raw_output: str,
) -> ValidatedInsightDTO:
    parsed = _parse_output(raw_output)
    title = str(parsed.get("summary", "Advisory insight"))[:255]
    summary = str(parsed.get("summary", raw_output[:2000]))[:4000]
    bullets = [str(b)[:500] for b in parsed.get("bullets", []) if b]

    unsupported: list[str] = []
    metrics = grounded.metrics_snapshot
    known_revenue = metrics.get("total_revenue")
    for match in _CURRENCY_CLAIM.finditer(raw_output):
        token = match.group(0)
        if known_revenue is None and token:
            unsupported.append(f"numeric claim without revenue evidence: {token[:40]}")

    stale = grounded.degraded_mode or grounded.rebuild_running_count > 0
    evidence_complete = len(grounded.evidence) > 0
    confidence_hint = float(parsed.get("confidence_hint", 0.75))
    confidence = Decimal(str(max(0.1, min(0.95, confidence_hint))))
    if stale:
        confidence = min(confidence, Decimal("0.6"))
    if unsupported:
        confidence = min(confidence, Decimal("0.5"))
    if not evidence_complete:
        confidence = min(confidence, Decimal("0.55"))

    return ValidatedInsightDTO(
        title=title,
        summary=summary,
        bullets=bullets,
        confidence=confidence,
        degraded_mode=grounded.degraded_mode,
        stale_data_warning=stale,
        unsupported_claims=unsupported,
        evidence_complete=evidence_complete,
        workflow=workflow,
        semantics_version=grounded.semantics_version,
        raw_model_output=raw_output[:8000],
    )


def _parse_output(raw: str) -> dict:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    return {"summary": raw[:2000], "bullets": []}

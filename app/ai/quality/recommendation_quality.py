"""Recommendation quality engine (post-processing; no new orchestration).

Goals:
- reduce generic/repetitive advice
- normalize confidence under stale / low-evidence contexts
- produce seller-readable actionable fields (V4B)
- compute fingerprint for duplicate suppression + fatigue tracking
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal

from app.ai.product.fatigue import FatigueAssessment
from app.ai.product.seller_intelligence import build_actionable_payload
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO

GENERIC_PATTERNS = (
    r"\boptimize\b",
    r"\bimprove\b",
    r"\bconsider\b",
    r"\breview\b",
    r"\bmonitor\b",
    r"\btry\b",
    r"\bbest practices\b",
)


@dataclass(frozen=True)
class QualityResult:
    fingerprint: str
    why_this_matters: str
    recommended_action: str
    impact_estimate: dict
    confidence: Decimal
    priority_score: Decimal
    flags: list[str]
    seller_usefulness: dict
    fatigue: FatigueAssessment | None = None


def _normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s[:800]


def compute_fingerprint(
    *,
    workflow: str,
    title: str,
    summary: str,
    evidence_ids: tuple[str, ...],
    metrics_snapshot: dict | None = None,
) -> str:
    snap = metrics_snapshot or {}
    report_id = str(snap.get("report_id") or "")
    period = f"{snap.get('source_period_start', '')}:{snap.get('source_period_end', '')}"
    compare = (
        f"{snap.get('requested_compare_period_start') or snap.get('compare_period_start', '')}:"
        f"{snap.get('requested_compare_period_end') or snap.get('compare_period_end', '')}"
    )
    revenue = str(snap.get("total_revenue") or "")
    compare_mode = str(snap.get("compare_mode") or "")
    deep_hash = hashlib.sha256(
        "|".join(str(x) for x in (snap.get("deep_insights") or [])[:3]).encode("utf-8")
    ).hexdigest()[:12]
    base = "|".join(
        [
            _normalize_text(workflow),
            _normalize_text(report_id),
            _normalize_text(period),
            _normalize_text(compare),
            _normalize_text(compare_mode),
            _normalize_text(revenue),
            deep_hash,
            "causal_v1",
            "|".join(sorted(_normalize_text(e) for e in evidence_ids))[:1200],
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _is_generic(summary: str) -> bool:
    s = summary.lower()
    return any(re.search(p, s) for p in GENERIC_PATTERNS) and len(s) < 240


def apply_quality(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    fatigue: FatigueAssessment | None = None,
) -> QualityResult:
    flags: list[str] = []

    evidence_ids = tuple(ref.source_id for ref in grounded.evidence)
    fp = compute_fingerprint(
        workflow=validated.workflow.value,
        title=scored.title,
        summary=scored.summary,
        evidence_ids=evidence_ids,
        metrics_snapshot=dict(grounded.metrics_snapshot),
    )

    conf = Decimal(scored.confidence)
    if grounded.degraded_mode or grounded.rebuild_running_count > 0:
        flags.append("stale_or_degraded_context")
        conf *= Decimal("0.75")
    if not grounded.evidence:
        flags.append("no_evidence")
        conf *= Decimal("0.70")
    if _is_generic(scored.summary):
        flags.append("generic_wording")
        conf *= Decimal("0.80")
    if scored.contradictions:
        flags.append("contradictions")
        conf *= Decimal("0.60")
    if scored.unsupported_claims:
        flags.append("unsupported_claims")
        conf *= Decimal("0.65")

    fatigue_penalty = 0.0
    novelty = 1.0
    if fatigue is not None:
        fatigue_penalty = fatigue.fatigue_penalty
        novelty = fatigue.novelty_score
        if fatigue.cooldown_active:
            flags.append("fatigue_cooldown")
        if fatigue.decay_applied:
            flags.append("fatigue_decay")
        if fatigue.should_suppress_duplicate:
            flags.append("fatigue_suppress")
        conf *= Decimal(str(max(0.5, novelty)))

    priority = Decimal(scored.priority_score)
    priority = min(Decimal("100"), max(Decimal("0"), priority * (conf + Decimal("0.20"))))
    if fatigue_penalty:
        priority = max(Decimal("0"), priority - Decimal(str(fatigue_penalty)))

    seller_payload = build_actionable_payload(
        scored=scored,
        validated=validated,
        grounded=grounded,
        flags=flags,
        fatigue_penalty=fatigue_penalty,
        novelty_score=novelty,
    )
    pri = seller_payload.get("prioritization") or {}
    priority = Decimal(str(pri.get("recommendation_score", priority)))

    conf = min(Decimal("1"), max(Decimal("0"), conf))

    impact = {
        "revenue_opportunity_score": str(scored.revenue_opportunity_score),
        "priority_score": str(priority),
        "confidence": str(conf),
        **seller_payload.get("measurable_impact", {}),
        "expected_business_impact": seller_payload.get("expected_business_impact"),
        "urgency": seller_payload.get("urgency"),
        "urgency_score": seller_payload.get("urgency_score"),
    }

    return QualityResult(
        fingerprint=fp,
        why_this_matters=seller_payload["why_this_matters"],
        recommended_action=seller_payload["recommended_action"],
        impact_estimate=impact,
        confidence=conf,
        priority_score=priority,
        flags=flags,
        seller_usefulness=seller_payload,
        fatigue=fatigue,
    )

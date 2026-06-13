"""Insight quality classification and scoring (Phase 6.2.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class StatementKind(StrEnum):
    KPI_STATEMENT = "KPI Statement"
    INSIGHT_STATEMENT = "Insight Statement"


@dataclass(frozen=True)
class EchoDetection:
    echo_detected: bool
    pattern: str | None
    has_causal_analysis: bool


@dataclass(frozen=True)
class InsightQualityScore:
    causal_depth: float
    business_relevance: float
    actionability: float
    confidence: float
    overall: float

    def to_dict(self) -> dict[str, float]:
        return {
            "causal_depth": self.causal_depth,
            "business_relevance": self.business_relevance,
            "actionability": self.actionability,
            "confidence": self.confidence,
            "overall": self.overall,
        }


_KPI_OPENERS = (
    "общий доход",
    "общая прибыль",
    "выручка за период",
    "выручка составила",
    "продажи составили",
    "маржа составила",
    "reported revenue",
    "governed revenue",
)

_CAUSAL_MARKERS = (
    "главный фактор",
    "из-за",
    "из‑за",
    "драйвер",
    "вклад",
    "компенсировали",
    "п.п.",
    "sku",
    "артикул",
    "убыточ",
    "логистик",
    "возврат",
    "концентрац",
    "себестоим",
    "комисс",
    "структур",
    "микса",
)


def classify_statement_kind(text: str) -> StatementKind:
    if not text or not text.strip():
        return StatementKind.KPI_STATEMENT
    if _has_causal_analysis(text):
        return StatementKind.INSIGHT_STATEMENT
    low = text.lower().strip()
    if any(p in low for p in _KPI_OPENERS):
        return StatementKind.KPI_STATEMENT
    if re.search(r"составил[аи]?\s+\d", low) or re.search(r"составля\w+\s+\d", low):
        if not _has_causal_analysis(text):
            return StatementKind.KPI_STATEMENT
    if re.search(r"sku|артикул", low, re.I) and re.search(r"\d", text):
        return StatementKind.INSIGHT_STATEMENT
    if "→" in text or "—" in text:
        return StatementKind.INSIGHT_STATEMENT
    return StatementKind.INSIGHT_STATEMENT if len(text) > 80 and _has_causal_analysis(text) else StatementKind.KPI_STATEMENT


def detect_echo_pattern(text: str, snap: dict | None = None) -> EchoDetection:
    snap = snap or {}
    low = text.lower()
    has_causal = _has_causal_analysis(text)
    matched: str | None = None
    for pattern in _KPI_OPENERS:
        if pattern in low:
            matched = pattern
            break
    if matched is None:
        if re.search(r"(выручка|доход|продажи|маржа)\s+(за\s+)?(период\s+)?составил", low):
            matched = "kpi_total_pattern"
    if matched is None:
        rev = str(snap.get("total_revenue") or "").replace(".", "")
        if rev and len(rev) >= 4:
            digits = re.sub(r"\D", "", text)
            if rev[:5] in digits and not has_causal:
                matched = "total_revenue_digits"
    echo = matched is not None and not has_causal
    return EchoDetection(echo_detected=echo, pattern=matched, has_causal_analysis=has_causal)


def compute_insight_quality_score(
    *,
    what_happened: str,
    why: str,
    action: str,
    confidence: float,
    priority_level: int,
) -> InsightQualityScore:
    causal = 0.0
    if why.strip() and why.strip() != what_happened.strip():
        causal += 12.0
    if _has_causal_analysis(f"{what_happened} {why}"):
        causal += 13.0
    causal = min(25.0, causal)

    business = 8.0
    if priority_level == 1:
        business += 17.0
    elif priority_level == 2:
        business += 10.0
    else:
        business += 3.0
    business = min(25.0, business)

    act = 0.0
    low = action.lower()
    if len(action.strip()) >= 20:
        act += 10.0
    if any(v in low for v in ("проверьте", "сверьте", "оцените", "рассмотрите", "загрузите", "измените", "улучшите")):
        act += 10.0
    if re.search(r"sku|артикул|\d", action, re.I):
        act += 5.0
    act = min(25.0, act)

    conf = min(25.0, max(0.0, confidence) * 25.0)
    overall = round(min(100.0, causal + business + act + conf), 1)
    return InsightQualityScore(
        causal_depth=round(causal, 1),
        business_relevance=round(business, 1),
        actionability=round(act, 1),
        confidence=round(conf, 1),
        overall=overall,
    )


def _has_causal_analysis(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in _CAUSAL_MARKERS)


def audit_text_fields(fields: dict[str, str], snap: dict | None = None) -> dict[str, Any]:
    """Classify title/summary fragments for audit reports."""
    kpi = 0
    insight = 0
    echoes: list[dict] = []
    for name, text in fields.items():
        if not text:
            continue
        kind = classify_statement_kind(text)
        if kind == StatementKind.KPI_STATEMENT:
            kpi += 1
        else:
            insight += 1
        echo = detect_echo_pattern(text, snap)
        if echo.echo_detected:
            echoes.append({"field": name, "pattern": echo.pattern, "preview": text[:120]})
    total = kpi + insight or 1
    return {
        "kpi_statement_count": kpi,
        "insight_statement_count": insight,
        "kpi_statement_rate_pct": round(kpi / total * 100, 1),
        "insight_statement_rate_pct": round(insight / total * 100, 1),
        "echo_detected": bool(echoes),
        "echo_fields": echoes,
    }

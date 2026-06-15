"""Unit tests for seller presentation layer."""

from __future__ import annotations

from decimal import Decimal

from app.ai.presentation.seller_display import (
    confidence_label_ru,
    sanitize_domain_insight_for_seller,
    seller_what_happened,
)
from app.dto.domain_analyst_dto import DomainFindingDTO


def test_confidence_label_ru_bands() -> None:
    assert confidence_label_ru(0.9) == "Высокая"
    assert confidence_label_ru(0.7) == "Средняя"
    assert confidence_label_ru(0.5) == "Низкая"


def test_seller_what_happened_prefers_russian_action() -> None:
    finding = DomainFindingDTO(
        finding_id="logistics_high_share",
        statement="Logistics burden 18.2% of revenue exceeds 15% benchmark.",
        confidence=Decimal("0.88"),
        severity="high",
        evidence_refs=["kpi:logistics"],
        recommended_actions=["Логистика составляет 18.2% выручки — проверьте тарифы WB."],
    )
    text = seller_what_happened(finding)
    assert "Логистика" in text
    assert "Logistics" not in text


def test_sanitize_domain_insight_strips_internal_fields() -> None:
    raw = {
        "insight_id": "logistics_analyst:logistics_high_share",
        "analyst_id": "logistics_analyst",
        "analyst_label": "Logistics Analyst",
        "statement": "Logistics burden 18.2% of revenue exceeds 15% benchmark.",
        "confidence": "0.88",
        "severity": "high",
        "priority_rank": 1,
        "reasoning_summary": "Logistics Analyst assigned severity high with confidence 0.88.",
        "recommended_actions": ["Проверьте габариты SKU."],
    }
    clean = sanitize_domain_insight_for_seller(raw)
    assert clean["domain"] == "Логистика"
    assert "Logistics Analyst" not in clean["statement"]
    assert "severity" not in clean
    assert "confidence" not in clean
    assert "reasoning_summary" not in clean
    assert "assigned severity" not in str(clean)

"""Insight-driven recommendation layer (Phase 6.2.2)."""

from app.ai.insights.composer import InsightDrivenOutput, compose_insight_driven_output
from app.ai.insights.quality import (
    InsightQualityScore,
    StatementKind,
    classify_statement_kind,
    compute_insight_quality_score,
    detect_echo_pattern,
)

__all__ = [
    "InsightDrivenOutput",
    "compose_insight_driven_output",
    "InsightQualityScore",
    "StatementKind",
    "classify_statement_kind",
    "compute_insight_quality_score",
    "detect_echo_pattern",
]

"""Model routing — FAST / REASONING / CHEAP roles (governed, no autonomous actions)."""

from __future__ import annotations

from enum import StrEnum

from app.core.config import settings
from app.dto.ai_analytics_dto import AnalyticsWorkflow


class ModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"
    CHEAP = "cheap"


_REASONING_WORKFLOWS = frozenset(
    {
        AnalyticsWorkflow.CAUSAL_ANALYSIS.value,
        AnalyticsWorkflow.RISK_DETECTION.value,
        AnalyticsWorkflow.RECOMMENDATION.value,
        AnalyticsWorkflow.ANOMALY_EXPLANATION.value,
    }
)


def resolve_model(
    *,
    role: ModelRole | None = None,
    workflow: str | None = None,
    streaming: bool = False,
) -> tuple[str, ModelRole]:
    """Return (model_name, role_used)."""
    if role is None:
        if streaming:
            role = ModelRole.FAST
        elif workflow in _REASONING_WORKFLOWS:
            role = ModelRole.REASONING
        else:
            role = ModelRole.FAST

    if role == ModelRole.REASONING and settings.ai_reasoning_model:
        return settings.ai_reasoning_model, role
    if role == ModelRole.FAST and settings.ai_fast_model:
        return settings.ai_fast_model, role
    if role == ModelRole.CHEAP and settings.ai_cheap_model:
        return settings.ai_cheap_model, role

    return settings.ai_openai_model or "gpt-4o-mini", role


def role_for_workflow(workflow: str, *, streaming: bool = False) -> ModelRole:
    if streaming:
        return ModelRole.FAST
    if workflow in _REASONING_WORKFLOWS:
        return ModelRole.REASONING
    return ModelRole.FAST

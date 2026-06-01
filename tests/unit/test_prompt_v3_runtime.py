"""Unit tests for prompt runtime v3 and model router."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.ai.evaluation.prompt_v3_suite import run_prompt_v3_eval_suite
from app.ai.prompts.v3.registry import PromptRegistryV3
from app.ai.prompts.v3.render import render_prompt_v3
from app.ai.providers.model_router import ModelRole, resolve_model
from app.dto.ai_analytics_dto import GroundedContextDTO


def _grounded() -> GroundedContextDTO:
    return GroundedContextDTO(
        semantics_version="1.0",
        data_as_of=datetime.now(UTC),
        source_period_start=date.today(),
        source_period_end=date.today(),
        degraded_mode=False,
        rebuild_pending_count=0,
        rebuild_running_count=0,
        metrics_snapshot={"total_revenue": "100"},
    )


def test_v3_registry_active_prompts() -> None:
    active = PromptRegistryV3.list_active()
    assert any(c.prompt_id == "v3.analytics.summary" for c in active)


def test_render_v3_includes_json_schema() -> None:
    r = render_prompt_v3(grounded=_grounded(), workflow="revenue_insight")
    assert "confidence_hint" in r.system
    assert r.prompt_id.startswith("v3.")


def test_model_router_reasoning_workflow() -> None:
    model, role = resolve_model(workflow="causal_analysis", streaming=False)
    assert role == ModelRole.REASONING
    assert model


def test_prompt_v3_eval_suite() -> None:
    results = run_prompt_v3_eval_suite()
    assert all(ok for _, ok in results), results

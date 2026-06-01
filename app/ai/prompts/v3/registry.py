"""Prompt registry v3 — versioning, active/inactive, labels, rollback metadata."""

from __future__ import annotations

from app.ai.prompts.v3.contracts import PromptContractV3

_REGISTRY: dict[str, PromptContractV3] = {
    "v3.analytics.summary": PromptContractV3(
        prompt_id="v3.analytics.summary",
        version="3.0.0",
        label="production",
        active=True,
        workflow="revenue_insight",
        input_schema="GroundedContextDTO.metrics_snapshot",
        output_schema="AnalyticalInsightJSONv3",
        evaluation_notes="Requires evidence_refs when metrics present",
        rollback_target="analytics.summary.v1",
    ),
    "v3.anomaly.investigation": PromptContractV3(
        prompt_id="v3.anomaly.investigation",
        version="3.0.0",
        label="production",
        active=True,
        workflow="anomaly_explanation",
        input_schema="GroundedContextDTO + anomalies",
        output_schema="AnalyticalInsightJSONv3",
        evaluation_notes="Stale data must reduce confidence",
        rollback_target="anomaly.investigation.v1",
    ),
    "v3.inventory.insight": PromptContractV3(
        prompt_id="v3.inventory.insight",
        version="3.0.0",
        label="production",
        active=True,
        workflow="inventory_insight",
        input_schema="GroundedContextDTO.metrics_snapshot",
        output_schema="AnalyticalInsightJSONv3",
        evaluation_notes="No hallucinated stock levels",
        rollback_target="inventory.insight.v1",
    ),
    "v3.reporting.executive": PromptContractV3(
        prompt_id="v3.reporting.executive",
        version="3.0.0",
        label="beta",
        active=True,
        workflow="recommendation",
        input_schema="GroundedContextDTO",
        output_schema="AnalyticalInsightJSONv3",
        evaluation_notes="Executive prioritization quality",
        rollback_target="reporting.executive.v1",
    ),
    # Inactive example for rollback testing
    "v3.analytics.summary.legacy": PromptContractV3(
        prompt_id="v3.analytics.summary.legacy",
        version="3.0.0-beta",
        label="inactive",
        active=False,
        workflow="revenue_insight",
        input_schema="GroundedContextDTO.metrics_snapshot",
        output_schema="AnalyticalInsightJSONv3",
        evaluation_notes="superseded by v3.analytics.summary",
        rollback_target="analytics.summary.v1",
    ),
}

_WORKFLOW_MAP: dict[str, str] = {
    "anomaly_explanation": "v3.anomaly.investigation",
    "risk_detection": "v3.anomaly.investigation",
    "inventory_insight": "v3.inventory.insight",
    "recommendation": "v3.reporting.executive",
    "revenue_insight": "v3.analytics.summary",
    "trend_explanation": "v3.analytics.summary",
    "causal_analysis": "v3.reporting.executive",
    "forecast_prep": "v3.analytics.summary",
}


class PromptRegistryV3:
    @classmethod
    def get(cls, prompt_id: str) -> PromptContractV3:
        c = _REGISTRY.get(prompt_id)
        if c is None:
            raise KeyError(f"unknown v3 prompt_id: {prompt_id}")
        return c

    @classmethod
    def resolve_for_workflow(cls, workflow: str) -> PromptContractV3:
        pid = _WORKFLOW_MAP.get(workflow, "v3.analytics.summary")
        contract = cls.get(pid)
        if not contract.active:
            raise KeyError(f"prompt {pid} is inactive")
        return contract

    @classmethod
    def list_active(cls) -> list[PromptContractV3]:
        return [c for c in _REGISTRY.values() if c.active]

    @classmethod
    def list_all(cls) -> list[PromptContractV3]:
        return list(_REGISTRY.values())

"""Prompt runtime v3 rendering — structured analytical contracts only."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.ai.prompts.v3.contracts import (
    ACTIONABILITY_RULES,
    GOVERNANCE_RULES,
    LOCALE_RULES,
    OUTPUT_SCHEMA_V3,
    PRIORITIZATION_RULES,
    SEVERITY_RULES,
)
from app.ai.prompts.v3.registry import PromptRegistryV3


@dataclass(frozen=True)
class RenderedPromptV3:
    system: str
    user: str
    prompt_id: str
    prompt_version: str
    template_id: str
    template_version: str = "3.0.0"
    output_schema: str = "AnalyticalInsightJSONv3"


def render_prompt_v3(*, grounded, workflow: str) -> RenderedPromptV3:
    contract = PromptRegistryV3.resolve_for_workflow(workflow)
    evidence_lines = [
        f"- {e.source_type}:{e.source_id} ({e.label})" for e in (grounded.evidence or ())[:20]
    ]
    system = "\n".join(
        [
            "You are a governed marketplace analytics advisor (NOT a chat assistant).",
            f"Prompt: {contract.prompt_id} v{contract.version} label={contract.label}",
            GOVERNANCE_RULES.strip(),
            LOCALE_RULES.strip(),
            SEVERITY_RULES.strip(),
            ACTIONABILITY_RULES.strip(),
            PRIORITIZATION_RULES.strip(),
            OUTPUT_SCHEMA_V3.strip(),
            f"Semantics: {grounded.semantics_version}",
            f"Data as-of: {grounded.data_as_of.isoformat()}",
            f"Period: {grounded.source_period_start} .. {grounded.source_period_end}",
            f"Freshness: {grounded.freshness_note}",
            f"Degraded mode: {grounded.degraded_mode}",
            f"Rebuild pending: {grounded.rebuild_pending_count}, running: {grounded.rebuild_running_count}",
            "Evidence refs (governed):",
            *(evidence_lines or ["- none"]),
        ]
    )
    user_payload = {
        "workflow": workflow,
        "metrics_snapshot": grounded.metrics_snapshot,
        "instruction": (
            "Analyze ONLY the metrics_snapshot and evidence. "
            "Produce JSON per schema. No markdown."
        ),
    }
    user = json.dumps(user_payload, default=str)[:8000]
    return RenderedPromptV3(
        system=system,
        user=user,
        prompt_id=contract.prompt_id,
        prompt_version=contract.version,
        template_id=f"v3:{contract.prompt_id}",
    )

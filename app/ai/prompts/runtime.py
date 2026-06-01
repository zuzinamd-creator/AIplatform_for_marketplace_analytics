"""Deterministic prompt rendering for governed AI runs.

This keeps prompt "contracts" (registry) separate from "templates" (rendering).
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedPrompt:
    system: str
    user: str
    template_id: str
    template_version: str


TEMPLATE_VERSION = "1.0.0"


def render_prompt(*, grounded, workflow: str) -> RenderedPrompt:
    from app.core.config import settings

    if getattr(settings, "ai_prompt_runtime_version", "v1") == "v3":
        from app.ai.prompts.v3.render import render_prompt_v3

        v3 = render_prompt_v3(grounded=grounded, workflow=workflow)
        return RenderedPrompt(
            system=v3.system,
            user=v3.user,
            template_id=v3.template_id,
            template_version=v3.template_version,
        )

    # v1 fallback — deterministic minimal template
    system = (
        "You are an advisory analytics assistant. "
        "Never mutate ledgers or claim authoritative financial truth. "
        f"Semantics version: {grounded.semantics_version}. "
        f"Data as-of: {grounded.data_as_of.isoformat()}. "
        f"Source period: {grounded.source_period_start} .. {grounded.source_period_end}. "
        f"Freshness: {grounded.freshness_note}. "
        f"Degraded mode: {grounded.degraded_mode}. "
        f"Workflow: {workflow}. "
        "Respond in JSON with keys: summary, bullets, confidence_hint."
    )

    # Deterministic user payload: JSON metrics snapshot.
    user = json.dumps(grounded.metrics_snapshot, default=str)[:6000]
    return RenderedPrompt(
        system=system,
        user=user,
        template_id=f"system+metrics_snapshot:{workflow}",
        template_version=TEMPLATE_VERSION,
    )


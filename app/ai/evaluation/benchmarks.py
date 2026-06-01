"""Deterministic evaluation fixtures for AI intelligence."""

from __future__ import annotations

from app.ai.evaluation.runner import EvalCase

INTELLIGENCE_EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        prompt_id="analytics.summary.v1",
        expected_contains=("advisory",),
        sample_output='{"summary": "Advisory revenue insight", "bullets": [], "confidence_hint": 0.8}',
    ),
    EvalCase(
        prompt_id="anomaly.investigation.v1",
        expected_contains=("anomaly",),
        sample_output='{"summary": "Anomaly pattern detected in metrics", "confidence_hint": 0.7}',
    ),
)


async def run_intelligence_eval_suite() -> list[tuple[str, bool]]:
    from app.ai.evaluation.runner import run_eval_case

    results: list[tuple[str, bool]] = []
    for case in INTELLIGENCE_EVAL_CASES:
        results.append((case.prompt_id, await run_eval_case(case)))
    return results

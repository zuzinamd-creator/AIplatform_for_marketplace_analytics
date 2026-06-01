"""Deterministic AI evaluation runner (prompt regression)."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.providers import get_evaluation_adapter
from app.ai.providers.types import EvaluationRequest


@dataclass(frozen=True)
class EvalCase:
    prompt_id: str
    expected_contains: tuple[str, ...]
    sample_output: str


async def run_eval_case(case: EvalCase) -> bool:
    adapter = get_evaluation_adapter()
    result = await adapter.evaluate(
        EvaluationRequest(
            prompt_id=case.prompt_id,
            expected_contains=case.expected_contains,
            actual=case.sample_output,
        )
    )
    return result.passed

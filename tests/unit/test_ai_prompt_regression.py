"""Prompt regression via evaluation adapter."""

from __future__ import annotations

import pytest
from app.ai.evaluation import EvalCase, run_eval_case


@pytest.mark.asyncio
async def test_analytics_summary_regression() -> None:
    passed = await run_eval_case(
        EvalCase(
            prompt_id="analytics.summary.v1",
            expected_contains=("summary",),
            sample_output='{"summary":"Advisory analysis","bullets":[],"confidence_hint":0.85}',
        )
    )
    assert passed is True

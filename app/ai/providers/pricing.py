"""Token cost estimation for common OpenAI-compatible models.

This is an estimate for product validation and budget visibility only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    prompt_per_1k: float
    completion_per_1k: float
    currency: str = "USD"


# NOTE: Keep conservative defaults; unknown models treated as zero-cost estimate.
PRICING: dict[str, ModelPricing] = {
    # Example pricing placeholders; adjust to your provider's actual price sheet.
    "gpt-4o-mini": ModelPricing(prompt_per_1k=0.00015, completion_per_1k=0.0006),
    "gpt-4o": ModelPricing(prompt_per_1k=0.0025, completion_per_1k=0.0100),
}


def estimate_cost_usd(*, model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    pricing = PRICING.get(model)
    if pricing is None:
        return None
    return (prompt_tokens / 1000.0) * pricing.prompt_per_1k + (completion_tokens / 1000.0) * pricing.completion_per_1k


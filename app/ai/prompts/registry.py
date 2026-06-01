"""Versioned prompt contracts (no embedded LLM calls)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptContract:
    prompt_id: str
    version: str
    purpose: str
    output_schema: str
    deterministic_sections: frozenset[str]
    probabilistic_sections: frozenset[str]


class PromptRegistry:
    """In-code registry — changes require prompt review per docs/ai/prompt_contracts.md."""

    _CONTRACTS: dict[str, PromptContract] = {
        "analytics.summary.v1": PromptContract(
            prompt_id="analytics.summary.v1",
            version="1.0.0",
            purpose="Summarize report-level KPIs from AIInsightInputDTO",
            output_schema="AIInsight.summary + bullets",
            deterministic_sections=frozenset({"metrics_table", "anomaly_list"}),
            probabilistic_sections=frozenset({"narrative_summary", "recommendations"}),
        ),
        "anomaly.investigation.v1": PromptContract(
            prompt_id="anomaly.investigation.v1",
            version="1.0.0",
            purpose="Explain ETL anomalies with ops context",
            output_schema="investigation_report",
            deterministic_sections=frozenset({"anomaly_ids", "severity_counts"}),
            probabilistic_sections=frozenset({"root_cause_hypothesis"}),
        ),
        "inventory.insight.v1": PromptContract(
            prompt_id="inventory.insight.v1",
            version="1.0.0",
            purpose="Inventory loss and discrepancy advisory",
            output_schema="inventory_advisory",
            deterministic_sections=frozenset({"loss_totals", "discrepancy_list"}),
            probabilistic_sections=frozenset({"optimization_suggestions"}),
        ),
        "forecast.prep.v1": PromptContract(
            prompt_id="forecast.prep.v1",
            version="1.0.0",
            purpose="Forecast preparation narrative (non-authoritative)",
            output_schema="forecast_prep",
            deterministic_sections=frozenset({"historical_period"}),
            probabilistic_sections=frozenset({"forecast_narrative"}),
        ),
        "reporting.executive.v1": PromptContract(
            prompt_id="reporting.executive.v1",
            version="1.0.0",
            purpose="Executive narrative for tenant stakeholders",
            output_schema="executive_summary",
            deterministic_sections=frozenset({"period", "totals"}),
            probabilistic_sections=frozenset({"executive_narrative"}),
        ),
    }

    @classmethod
    def get(cls, prompt_id: str) -> PromptContract:
        contract = cls._CONTRACTS.get(prompt_id)
        if contract is None:
            raise KeyError(f"unknown prompt_id: {prompt_id}")
        return contract

    @classmethod
    def list_ids(cls) -> list[str]:
        return sorted(cls._CONTRACTS.keys())


def get_prompt_contract(prompt_id: str) -> PromptContract:
    return PromptRegistry.get(prompt_id)

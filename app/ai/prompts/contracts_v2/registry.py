"""Prompt contract registry v2 — per domain analyst."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptContractV2:
    prompt_id: str
    version: str
    analyst_id: str
    purpose: str
    input_schema: str
    output_schema: str
    evaluation_examples: tuple[str, ...]
    metadata: dict[str, str]


class PromptContractRegistryV2:
    _CONTRACTS: dict[str, PromptContractV2] = {
        "analyst.sales.v2": PromptContractV2(
            prompt_id="analyst.sales.v2",
            version="2.0.0",
            analyst_id="sales_analyst",
            purpose="Interpret governed sales KPI slice (no metric computation)",
            input_schema="AnalyticalIntelligencePackage.sales",
            output_schema="DomainAnalystOutputDTO",
            evaluation_examples=(
                '{"findings":[{"finding_id":"sales_revenue_present","confidence":0.9}]}',
            ),
            metadata={"layer": "domain", "advisory_only": "true"},
        ),
        "analyst.ads.v2": PromptContractV2(
            prompt_id="analyst.ads.v2",
            version="2.0.0",
            analyst_id="ads_analyst",
            purpose="Ad spend advisory when governed ad KPIs exist",
            input_schema="AnalyticalIntelligencePackage.ads",
            output_schema="DomainAnalystOutputDTO",
            evaluation_examples=('{"findings":[],"insufficient_data":true}',),
            metadata={"layer": "domain", "advisory_only": "true"},
        ),
        "analyst.funnel.v2": PromptContractV2(
            prompt_id="analyst.funnel.v2",
            version="2.0.0",
            analyst_id="funnel_analyst",
            purpose="SKU concentration and catalog breadth advisory",
            input_schema="AnalyticalIntelligencePackage.funnel",
            output_schema="DomainAnalystOutputDTO",
            evaluation_examples=("{}",),
            metadata={"layer": "domain", "advisory_only": "true"},
        ),
        "analyst.inventory.v2": PromptContractV2(
            prompt_id="analyst.inventory.v2",
            version="2.0.0",
            analyst_id="inventory_analyst",
            purpose="Inventory loss and stock advisory from governed signals",
            input_schema="AnalyticalIntelligencePackage.inventory",
            output_schema="DomainAnalystOutputDTO",
            evaluation_examples=("{}",),
            metadata={"layer": "domain", "advisory_only": "true"},
        ),
        "analyst.marketplace.v2": PromptContractV2(
            prompt_id="analyst.marketplace.v2",
            version="2.0.0",
            analyst_id="marketplace_comparison_analyst",
            purpose="Cross-marketplace comparison when multiple reports exist",
            input_schema="AnalyticalIntelligencePackage.marketplace",
            output_schema="DomainAnalystOutputDTO",
            evaluation_examples=("{}",),
            metadata={"layer": "domain", "advisory_only": "true"},
        ),
        "analyst.anomaly.v2": PromptContractV2(
            prompt_id="analyst.anomaly.v2",
            version="2.0.0",
            analyst_id="anomaly_analyst",
            purpose="Explain governed ETL anomalies",
            input_schema="AnalyticalIntelligencePackage.anomaly",
            output_schema="DomainAnalystOutputDTO",
            evaluation_examples=('{"findings":[{"severity":"high"}]}',),
            metadata={"layer": "domain", "advisory_only": "true"},
        ),
        "executive.aggregate.v2": PromptContractV2(
            prompt_id="executive.aggregate.v2",
            version="2.0.0",
            analyst_id="executive_intelligence",
            purpose="Merge domain outputs, resolve conflicts, prioritize for seller",
            input_schema="list[DomainAnalystOutputDTO]",
            output_schema="ExecutiveAggregationResultDTO",
            evaluation_examples=('{"prioritized_insights":[],"overall_confidence":0.5}',),
            metadata={"layer": "executive", "advisory_only": "true"},
        ),
    }

    @classmethod
    def get(cls, prompt_id: str) -> PromptContractV2:
        c = cls._CONTRACTS.get(prompt_id)
        if c is None:
            raise KeyError(f"unknown v2 prompt_id: {prompt_id}")
        return c

    @classmethod
    def list_ids(cls) -> list[str]:
        return sorted(cls._CONTRACTS.keys())

    @classmethod
    def for_analyst(cls, analyst_id: str) -> PromptContractV2 | None:
        for c in cls._CONTRACTS.values():
            if c.analyst_id == analyst_id:
                return c
        return None

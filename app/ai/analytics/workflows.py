"""Workflow → agent + prompt mapping."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.agents import AgentKind
from app.dto.ai_analytics_dto import AnalyticsWorkflow


@dataclass(frozen=True)
class WorkflowSpec:
    agent: AgentKind
    prompt_id: str


WORKFLOW_SPECS: dict[AnalyticsWorkflow, WorkflowSpec] = {
    AnalyticsWorkflow.ANOMALY_EXPLANATION: WorkflowSpec(
        AgentKind.ANOMALY_INVESTIGATION, "anomaly.investigation.v1"
    ),
    AnalyticsWorkflow.TREND_EXPLANATION: WorkflowSpec(
        AgentKind.ANALYTICS, "analytics.summary.v1"
    ),
    AnalyticsWorkflow.REVENUE_INSIGHT: WorkflowSpec(
        AgentKind.ANALYTICS, "analytics.summary.v1"
    ),
    AnalyticsWorkflow.INVENTORY_INSIGHT: WorkflowSpec(
        AgentKind.INVENTORY_OPTIMIZER, "inventory.insight.v1"
    ),
    AnalyticsWorkflow.CAUSAL_ANALYSIS: WorkflowSpec(
        AgentKind.ANALYTICS, "analytics.summary.v1"
    ),
    AnalyticsWorkflow.RECOMMENDATION: WorkflowSpec(
        AgentKind.RECOMMENDATION, "analytics.summary.v1"
    ),
    AnalyticsWorkflow.RISK_DETECTION: WorkflowSpec(
        AgentKind.ANOMALY_INVESTIGATION, "anomaly.investigation.v1"
    ),
    AnalyticsWorkflow.FORECAST_PREP: WorkflowSpec(
        AgentKind.FORECASTING_ASSISTANT, "forecast.prep.v1"
    ),
}


def spec_for(workflow: AnalyticsWorkflow) -> WorkflowSpec:
    return WORKFLOW_SPECS[workflow]

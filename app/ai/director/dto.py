"""Operating Director architecture DTOs (Phase 6.3 scaffold).

Layers:
  L0 Data Quality Auditor
  L1 Domain Experts
  L2 Cross-Domain Analysts
  L3 Executive Director → Seller Report
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SeverityLevel = Literal["low", "medium", "high", "critical"]


class DomainExpertId(StrEnum):
    SALES = "sales_analyst"
    MARKETPLACE_ECONOMICS = "marketplace_economics_analyst"
    UNIT_ECONOMICS = "unit_economics_analyst"
    ADVERTISING = "advertising_analyst"
    PRODUCT_CARD = "product_card_analyst"
    INVENTORY = "inventory_analyst"
    TAX = "tax_analyst"
    OPERATING_COST = "operating_cost_analyst"


class CrossDomainAnalystId(StrEnum):
    GROWTH = "growth_analyst"
    PROFIT = "profit_analyst"
    RISK = "risk_analyst"


class DataQualityAuditDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    coverage_score: Decimal = Field(ge=0, le=100)
    coverage_version: str = "v2"
    missing_blocks: list[str] = Field(default_factory=list)
    confidence_penalty: Decimal = Field(ge=0, le=1, default=Decimal("0"))
    allowed_analysts: list[str] = Field(default_factory=list)
    blocked_analysts: list[str] = Field(default_factory=list)
    coverage_formula: str = ""


class ActionableFindingDTO(BaseModel):
    """Every analyst must return actionable findings (no action-free advice)."""

    model_config = ConfigDict(strict=True)

    finding_id: str
    finding: str = Field(min_length=1, max_length=512)
    root_cause: str = Field(min_length=1, max_length=512)
    impact_estimate: str = Field(min_length=1, max_length=512)
    recommended_action: str = Field(min_length=1, max_length=512)
    confidence: Decimal = Field(ge=0, le=1)
    severity: SeverityLevel = "medium"
    evidence_refs: list[str] = Field(default_factory=list)


class DomainExpertOutputDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    analyst_id: DomainExpertId
    contract_version: str = "od_v1"
    ran: bool = False
    skip_reason: str | None = None
    findings: list[ActionableFindingDTO] = Field(default_factory=list, max_length=20)
    overall_confidence: Decimal = Field(ge=0, le=1, default=Decimal("0"))


class CrossDomainOutputDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    analyst_id: CrossDomainAnalystId
    contract_version: str = "od_v1"
    ran: bool = False
    skip_reason: str | None = None
    question: str = ""
    findings: list[ActionableFindingDTO] = Field(default_factory=list, max_length=15)
    upstream_analysts: list[str] = Field(default_factory=list)
    overall_confidence: Decimal = Field(ge=0, le=1, default=Decimal("0"))


class ExecutiveDirectorReportDTO(BaseModel):
    """Seller-facing report — built ONLY from analyst outputs, never raw KPI."""

    model_config = ConfigDict(strict=True)

    architecture_version: str = "operating_director_v1"
    period_label: str = ""
    top_conclusions: list[str] = Field(default_factory=list, max_length=3)
    main_causes: list[str] = Field(default_factory=list, max_length=5)
    top_risks: list[str] = Field(default_factory=list, max_length=3)
    top_actions: list[str] = Field(default_factory=list, max_length=3)
    analysis_limitations: str = ""
    quality_audit: DataQualityAuditDTO
    confidence: Decimal = Field(ge=0, le=1, default=Decimal("0.5"))


class OperatingDirectorTraceDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    quality_audit: DataQualityAuditDTO
    domain_outputs: list[DomainExpertOutputDTO] = Field(default_factory=list)
    cross_domain_outputs: list[CrossDomainOutputDTO] = Field(default_factory=list)
    executive_report: ExecutiveDirectorReportDTO | None = None

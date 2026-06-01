"""AI decision engine — scoring, prioritization, reasoning heuristics."""

from __future__ import annotations

from decimal import Decimal

from app.dto.ai_analytics_dto import AnalyticsWorkflow, GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import RiskClassification, ScoredRecommendationDTO


class AIDecisionEngine:
    """Deterministic scoring layer on top of validated insights (advisory-only)."""

    def score_recommendation(
        self,
        *,
        validated: ValidatedInsightDTO,
        grounded: GroundedContextDTO,
    ) -> ScoredRecommendationDTO:
        confidence = validated.confidence
        priority = self._priority_score(validated, grounded)
        revenue = self._revenue_opportunity(validated, grounded)
        risk = self._classify_risk(validated, grounded)
        requires_approval, category = self._approval_gate(validated.workflow, risk)

        return ScoredRecommendationDTO(
            title=validated.title,
            summary=validated.summary,
            bullets=validated.bullets,
            confidence=confidence,
            priority_score=priority,
            revenue_opportunity_score=revenue,
            risk_class=risk,
            requires_human_approval=requires_approval,
            approval_category=category,
            unsupported_claims=validated.unsupported_claims,
        )

    def _priority_score(
        self,
        validated: ValidatedInsightDTO,
        grounded: GroundedContextDTO,
    ) -> Decimal:
        base = float(validated.confidence) * 60.0
        if validated.workflow in (
            AnalyticsWorkflow.RISK_DETECTION,
            AnalyticsWorkflow.ANOMALY_EXPLANATION,
        ):
            base += 25.0
        if grounded.rebuild_pending_count > 0:
            base -= 10.0
        if validated.stale_data_warning:
            base -= 15.0
        return Decimal(str(max(0.0, min(100.0, base))))

    def _revenue_opportunity(
        self,
        validated: ValidatedInsightDTO,
        grounded: GroundedContextDTO,
    ) -> Decimal:
        if validated.workflow not in (
            AnalyticsWorkflow.REVENUE_INSIGHT,
            AnalyticsWorkflow.RECOMMENDATION,
        ):
            return Decimal("0")
        revenue = grounded.metrics_snapshot.get("total_revenue")
        if revenue is None:
            return Decimal("20")
        try:
            val = float(revenue)
            return Decimal(str(min(100.0, 30.0 + val / 10000.0)))
        except (TypeError, ValueError):
            return Decimal("25")

    def _classify_risk(
        self,
        validated: ValidatedInsightDTO,
        grounded: GroundedContextDTO,
    ) -> RiskClassification:
        if validated.unsupported_claims:
            return RiskClassification.HIGH
        if validated.workflow == AnalyticsWorkflow.RISK_DETECTION:
            return RiskClassification.MEDIUM
        if grounded.degraded_mode or validated.stale_data_warning:
            return RiskClassification.MEDIUM
        return RiskClassification.LOW

    def _approval_gate(
        self,
        workflow: AnalyticsWorkflow,
        risk: RiskClassification,
    ) -> tuple[bool, str | None]:
        if workflow == AnalyticsWorkflow.RECOMMENDATION:
            return True, "pricing_change"
        if risk in (RiskClassification.HIGH, RiskClassification.CRITICAL):
            return True, "high_risk_recommendation"
        return False, None

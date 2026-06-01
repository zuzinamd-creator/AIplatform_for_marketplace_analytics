"""Executive intelligence layer — merge, prioritize, and narrate domain analyst outputs."""

from __future__ import annotations

from decimal import Decimal

from app.dto.domain_analyst_dto import (
    ConflictResolutionNoteDTO,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
    ExecutiveAggregationResultDTO,
    ExecutiveInsightDTO,
)

_SEVERITY_WEIGHT = {
    "low": Decimal("10"),
    "medium": Decimal("25"),
    "high": Decimal("45"),
    "critical": Decimal("70"),
}

_ANALYST_LABELS = {
    "sales_analyst": "Sales Analyst",
    "ads_analyst": "Ads Analyst",
    "funnel_analyst": "Funnel Analyst",
    "inventory_analyst": "Inventory Analyst",
    "marketplace_comparison_analyst": "Marketplace Comparison Analyst",
    "anomaly_analyst": "Anomaly Analyst",
}


class ExecutiveIntelligenceAggregator:
    """Merge domain outputs, resolve contradictions, produce seller-facing narrative."""

    def aggregate(self, domain_outputs: list[DomainAnalystOutputDTO]) -> ExecutiveAggregationResultDTO:
        flat = self._flatten_findings(domain_outputs)
        conflicts, resolved_flat = self._resolve_contradictions(flat)
        prioritized = self._prioritize(resolved_flat)
        propagation = self._confidence_propagation(domain_outputs, prioritized)
        narrative = self._build_narrative(prioritized)
        recommendations = self._final_recommendations(prioritized)
        impact = self._business_impact_estimate(prioritized)

        overall = Decimal("0.5")
        if prioritized:
            overall = sum(i.confidence for i in prioritized[:5]) / Decimal(
                min(5, len(prioritized))
            )

        return ExecutiveAggregationResultDTO(
            narrative=narrative,
            executive_summary=narrative[:500],
            prioritized_insights=prioritized,
            final_recommendations=recommendations,
            overall_confidence=min(Decimal("1"), overall),
            business_impact_estimate=impact,
            conflicts_resolved=conflicts,
            confidence_propagation=propagation,
            domain_outputs=domain_outputs,
            aggregation_notes=[
                f"Merged {len(domain_outputs)} domain analyst outputs",
                f"Prioritized {len(prioritized)} insights after conflict resolution",
            ],
        )

    def _flatten_findings(
        self, outputs: list[DomainAnalystOutputDTO]
    ) -> list[tuple[DomainAnalystOutputDTO, DomainFindingDTO]]:
        items: list[tuple[DomainAnalystOutputDTO, DomainFindingDTO]] = []
        for out in outputs:
            for f in out.findings:
                items.append((out, f))
        return items

    def _resolve_contradictions(
        self,
        items: list[tuple[DomainAnalystOutputDTO, DomainFindingDTO]],
    ) -> tuple[list[ConflictResolutionNoteDTO], list[tuple[DomainAnalystOutputDTO, DomainFindingDTO]]]:
        """Suppress lower-confidence opposing actions on shared evidence refs."""
        conflicts: list[ConflictResolutionNoteDTO] = []
        suppressed: set[str] = set()
        by_evidence: dict[str, list[tuple[DomainAnalystOutputDTO, DomainFindingDTO]]] = {}
        for out, f in items:
            key = "|".join(sorted(f.evidence_refs)) or f.finding_id
            by_evidence.setdefault(key, []).append((out, f))

        for key, group in by_evidence.items():
            if len(group) < 2:
                continue
            actions = {tuple(f.recommended_actions) for _, f in group}
            if len(actions) <= 1:
                continue
            ranked = sorted(group, key=lambda x: x[1].confidence, reverse=True)
            winner = ranked[0]
            for loser_out, loser_f in ranked[1:]:
                if loser_f.finding_id in suppressed:
                    continue
                conflicts.append(
                    ConflictResolutionNoteDTO(
                        conflict_id=f"conflict_{key[:32]}_{loser_f.finding_id}",
                        analysts_involved=(
                            winner[0].analyst_id.value,
                            loser_out.analyst_id.value,
                        ),
                        resolution=(
                            f"Retained {winner[0].analyst_id.value} finding "
                            f"(confidence {winner[1].confidence}) over "
                            f"{loser_out.analyst_id.value} (confidence {loser_f.confidence})"
                        ),
                        retained_finding_id=winner[1].finding_id,
                        suppressed_finding_id=loser_f.finding_id,
                    )
                )
                suppressed.add(loser_f.finding_id)

        resolved = [(o, f) for o, f in items if f.finding_id not in suppressed]
        return conflicts, resolved

    def _prioritize(
        self,
        items: list[tuple[DomainAnalystOutputDTO, DomainFindingDTO]],
    ) -> list[ExecutiveInsightDTO]:
        scored: list[tuple[Decimal, DomainAnalystOutputDTO, DomainFindingDTO]] = []
        for out, f in items:
            score = _SEVERITY_WEIGHT.get(f.severity, Decimal("10")) * f.confidence
            scored.append((score, out, f))
        scored.sort(key=lambda x: x[0], reverse=True)

        insights: list[ExecutiveInsightDTO] = []
        for rank, (_, out, f) in enumerate(scored, start=1):
            impact = min(Decimal("100"), scored[rank - 1][0])
            insights.append(
                ExecutiveInsightDTO(
                    insight_id=f"{out.analyst_id.value}:{f.finding_id}",
                    analyst_id=out.analyst_id.value,
                    analyst_label=_ANALYST_LABELS.get(
                        out.analyst_id.value, out.analyst_id.value
                    ),
                    statement=f.statement,
                    confidence=f.confidence,
                    severity=f.severity,
                    priority_rank=rank,
                    evidence_refs=f.evidence_refs,
                    recommended_actions=f.recommended_actions,
                    business_impact_score=impact,
                    reasoning_summary=(
                        f"{_ANALYST_LABELS.get(out.analyst_id.value, out.analyst_id.value)} "
                        f"assigned severity {f.severity} with confidence {f.confidence}."
                    ),
                )
            )
        return insights

    def _confidence_propagation(
        self,
        outputs: list[DomainAnalystOutputDTO],
        insights: list[ExecutiveInsightDTO],
    ) -> dict[str, str]:
        prop: dict[str, str] = {}
        for out in outputs:
            prop[out.analyst_id.value] = f"analyst_confidence={out.overall_confidence}"
        if insights:
            top = insights[0]
            prop["executive_top_insight"] = (
                f"{top.analyst_id} rank=1 confidence={top.confidence}"
            )
        return prop

    def _build_narrative(self, insights: list[ExecutiveInsightDTO]) -> str:
        if not insights:
            return (
                "Executive intelligence: no domain findings in current governed package. "
                "Upload reports and refresh analytics before acting on advisory output."
            )
        parts = [f"Top priority ({i.analyst_label}): {i.statement}" for i in insights[:3]]
        return " ".join(parts)

    def _final_recommendations(self, insights: list[ExecutiveInsightDTO]) -> list[str]:
        recs: list[str] = []
        for ins in insights[:8]:
            for action in ins.recommended_actions:
                if action not in recs:
                    recs.append(action)
        return recs[:15]

    def _business_impact_estimate(self, insights: list[ExecutiveInsightDTO]) -> str:
        if not insights:
            return "low — insufficient governed findings"
        top = insights[0]
        if top.severity in ("high", "critical"):
            return f"elevated — {top.analyst_label} flagged {top.severity} severity"
        return "moderate — review prioritized domain insights before operational changes"

"""Analytical reasoning contracts for prompt runtime v3."""

from __future__ import annotations

from dataclasses import dataclass

OUTPUT_SCHEMA_V3 = """
Respond ONLY with valid JSON matching:
{
  "summary": "string (advisory, <= 400 chars)",
  "bullets": ["measurable action or observation", ...],
  "confidence_hint": 0.0-1.0,
  "why": "why this matters to the seller",
  "expected_impact": "business impact band: low|moderate|high",
  "urgency": "today|this_week|when_convenient",
  "recommended_actions": ["concrete operator step", ...],
  "evidence_refs": ["governed ref id", ...],
  "limitations": ["what AI cannot assert", ...]
}
"""

SEVERITY_RULES = """
Severity mapping (use in bullets, not free narrative):
- critical: data integrity blocks KPI trust
- high: revenue/margin risk with governed evidence
- medium: optimization opportunity
- low: informational
"""

ACTIONABILITY_RULES = """
Actionability rules:
- Each recommended_action must be verifiable outside the platform
- No imperative to change ledger or auto-apply pricing
- Reference governed metrics_snapshot keys when citing numbers
- If metrics_snapshot empty, state insufficient_data and lower confidence_hint
"""

PRIORITIZATION_RULES = """
Prioritization:
- Order bullets by severity then confidence_hint
- Max 5 bullets
- Deprioritize generic advice (optimize, consider, monitor) unless tied to evidence_refs
"""

GOVERNANCE_RULES = """
Governance (mandatory):
- NEVER invent KPIs not present in metrics_snapshot or evidence list
- NEVER claim financial authority — advisory only
- If degraded_mode or stale signals: cap confidence_hint <= 0.6 and note in limitations
- Unsupported claims must be listed in limitations, not bullets
"""

LOCALE_RULES = """
Language (mandatory for seller-facing text):
- Write summary, bullets, why, recommended_actions, and limitations in Russian.
- Keep JSON property names exactly as in the schema (English keys only).
- Keep enum values exactly: expected_impact = low|moderate|high; urgency = today|this_week|when_convenient.
- Format money as readable RUB (e.g. "1 001 290 ₽"), not raw long decimals.
- If margin in metrics_snapshot exceeds 100 or profit exceeds revenue, note data-quality caveat in limitations.
"""


@dataclass(frozen=True)
class PromptContractV3:
    prompt_id: str
    version: str
    label: str
    active: bool
    workflow: str
    input_schema: str
    output_schema: str
    evaluation_notes: str
    rollback_target: str | None = None

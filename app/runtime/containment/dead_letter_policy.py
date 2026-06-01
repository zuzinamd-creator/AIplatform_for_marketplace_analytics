"""Dead-letter escalation governance — explicit thresholds."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class DeadLetterEscalation:
    severity: str
    recommendation: str
    requires_operator: bool


class DeadLetterEscalationPolicy:
    @staticmethod
    def assess(*, dlq_count: int, tenant_dlq_count: int) -> DeadLetterEscalation:
        if tenant_dlq_count >= settings.reliability_tenant_quarantine_dlq_threshold:
            return DeadLetterEscalation(
                severity="critical",
                recommendation="Quarantine tenant and inspect poison payloads",
                requires_operator=True,
            )
        if dlq_count >= settings.reliability_global_dlq_warn_threshold:
            return DeadLetterEscalation(
                severity="warn",
                recommendation="Review global DLQ backlog and replay runbooks",
                requires_operator=True,
            )
        return DeadLetterEscalation(
            severity="ok",
            recommendation="Monitor DLQ via /ops/dead-letters",
            requires_operator=False,
        )

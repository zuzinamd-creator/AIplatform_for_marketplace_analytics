"""Operational simulation — dry-run without side effects."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.runtime.enterprise.coordinator import AutonomousOperationsEngine
from app.runtime.enterprise.dto import EnterpriseOpsCycleResult
from app.runtime.policy.engine import RuntimeOperationalPolicy


class OperationalSimulationEngine:
    """Dry-run wrapper for enterprise operations cycles."""

    def __init__(
        self,
        db: AsyncSession,
        *,
        policy: RuntimeOperationalPolicy | None = None,
    ) -> None:
        self._engine = AutonomousOperationsEngine(db, policy=policy)

    async def simulate_cycle(self) -> EnterpriseOpsCycleResult:
        return await self._engine.run_cycle(dry_run=True)

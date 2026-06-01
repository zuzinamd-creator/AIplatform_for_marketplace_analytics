"""Persist inventory integrity anomalies (additive escalation layer)."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory.integrity import InventoryIntegrityAnomaly, InventoryIntegrityAnomalyType


class InventoryIntegrityEscalationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def record(
        self,
        *,
        anomaly_type: InventoryIntegrityAnomalyType,
        snapshot_date: date | None = None,
        sku: str | None = None,
        warehouse_name: str | None = None,
        details: dict | None = None,
    ) -> InventoryIntegrityAnomaly:
        row = InventoryIntegrityAnomaly(
            id=uuid4(),
            user_id=self.user_id,
            anomaly_type=anomaly_type,
            snapshot_date=snapshot_date,
            sku=sku,
            warehouse_name=warehouse_name,
            details=details,
        )
        self.db.add(row)
        await self.db.flush()
        return row

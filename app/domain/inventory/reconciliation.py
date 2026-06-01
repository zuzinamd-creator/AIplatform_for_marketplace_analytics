from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.cost import cost_on_date
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.snapshot_types import (
    InventoryLossAnalytics,
    WarehouseDiscrepancySummary,
    WarehouseStockSnapshotDraft,
)
from app.models.inventory.enums import InventoryOperationType


class InventoryReconciliationService:
    """Valuate stock discrepancies using historical unit cost on snapshot_date."""

    @staticmethod
    def build_sale_price_index(
        movements: list[InventoryLedgerRow],
    ) -> dict[tuple[str | None, str | None, str | None, date], Decimal]:
        totals: dict[tuple[str | None, str | None, str | None, date], tuple[Decimal, int]] = {}
        for row in movements:
            if row.operation_type != InventoryOperationType.SALE:
                continue
            if row.sale_price_per_unit is None:
                continue
            key = (row.sku, row.nm_id, row.warehouse_name, row.operation_date)
            amount, units = totals.get(key, (Decimal("0"), 0))
            units_delta = abs(row.quantity_delta)
            unit_price = InventoryReconciliationService._decimal(row.sale_price_per_unit)
            totals[key] = (
                amount + unit_price * Decimal(units_delta),
                units + units_delta,
            )
        return {
            key: (amount / Decimal(units)).quantize(Decimal("0.0001"))
            for key, (amount, units) in totals.items()
            if units > 0
        }

    @staticmethod
    def _decimal(value: Decimal | int | str) -> Decimal:
        """Coerce to Decimal without float intermediate."""
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))

    @staticmethod
    def reconcile_snapshots(
        snapshots: list[WarehouseStockSnapshotDraft],
        *,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        sale_prices_by_key: dict[tuple[str | None, str | None, str | None, date], Decimal] | None = None,
    ) -> list[WarehouseStockSnapshotDraft]:
        sale_prices_by_key = sale_prices_by_key or {}
        reconciled: list[WarehouseStockSnapshotDraft] = []
        for snap in snapshots:
            unit_cost = InventoryReconciliationService._unit_cost(snap, costs_by_sku)
            unit_sale = sale_prices_by_key.get(
                (snap.sku, snap.nm_id, snap.warehouse_name, snap.snapshot_date),
            )
            disc_cost, disc_sale = InventoryReconciliationService._value_discrepancy(
                snap.discrepancy_units,
                unit_cost=unit_cost,
                unit_sale=unit_sale,
            )
            reconciled.append(
                WarehouseStockSnapshotDraft(
                    snapshot_date=snap.snapshot_date,
                    sku=snap.sku,
                    nm_id=snap.nm_id,
                    warehouse_name=snap.warehouse_name,
                    opening_stock=snap.opening_stock,
                    inbound_units=snap.inbound_units,
                    sold_units=snap.sold_units,
                    returned_units=snap.returned_units,
                    lost_units=snap.lost_units,
                    writeoff_units=snap.writeoff_units,
                    expected_closing_stock=snap.expected_closing_stock,
                    actual_stock=snap.actual_stock,
                    discrepancy_units=snap.discrepancy_units,
                    discrepancy_cost=disc_cost,
                    discrepancy_sale_value=disc_sale,
                )
            )
        return reconciled

    @staticmethod
    def build_loss_analytics(
        snapshots: list[WarehouseStockSnapshotDraft],
        *,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        limit_top_skus: int = 5,
    ) -> InventoryLossAnalytics:
        discrepancies = [
            WarehouseDiscrepancySummary(
                sku=snap.sku,
                nm_id=snap.nm_id,
                warehouse_name=snap.warehouse_name,
                snapshot_date=snap.snapshot_date,
                discrepancy_units=snap.discrepancy_units,
                discrepancy_cost=snap.discrepancy_cost,
                discrepancy_sale_value=snap.discrepancy_sale_value,
            )
            for snap in snapshots
            if snap.discrepancy_units != 0
        ]

        loss_units = sum(snap.lost_units for snap in snapshots) + sum(
            abs(snap.discrepancy_units) for snap in snapshots if snap.discrepancy_units != 0
        )

        loss_cost = Decimal("0")
        loss_sale = Decimal("0")
        sku_loss_cost: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for snap in snapshots:
            unit_cost = InventoryReconciliationService._unit_cost(snap, costs_by_sku) or Decimal("0")
            if snap.lost_units > 0 and snap.sku:
                lost_valuation = unit_cost * Decimal(snap.lost_units)
                loss_cost += lost_valuation
                sku_loss_cost[snap.sku] += lost_valuation
            if snap.discrepancy_units != 0:
                loss_cost += abs(snap.discrepancy_cost)
                loss_sale += abs(snap.discrepancy_sale_value)
                if snap.sku:
                    sku_loss_cost[snap.sku] += abs(snap.discrepancy_cost)

        top_loss_skus = sorted(sku_loss_cost.items(), key=lambda item: item[1], reverse=True)[
            :limit_top_skus
        ]

        return InventoryLossAnalytics(
            inventory_losses_units=loss_units,
            inventory_losses_cost=loss_cost,
            inventory_losses_sale_value=loss_sale,
            warehouse_discrepancies=discrepancies,
            top_loss_skus=top_loss_skus,
        )

    @staticmethod
    def _unit_cost(
        snap: WarehouseStockSnapshotDraft,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
    ) -> Decimal | None:
        if not snap.sku:
            return None
        return cost_on_date(costs_by_sku.get(snap.sku, []), snap.snapshot_date)

    @staticmethod
    def _value_discrepancy(
        discrepancy_units: int,
        *,
        unit_cost: Decimal | None,
        unit_sale: Decimal | None,
    ) -> tuple[Decimal, Decimal]:
        units = Decimal(discrepancy_units)
        cost = InventoryReconciliationService._decimal(unit_cost or Decimal("0"))
        sale = InventoryReconciliationService._decimal(unit_sale or Decimal("0"))
        return cost * units, sale * units

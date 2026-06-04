"""WB financial persist — raw, normalized, ledger, reconciliation layers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches
from app.etl.wb.serialize import serialize_payload
from app.etl.wb.stream_types import WbProcessChunk
from app.etl.wb.types import WbFinancialProcessResult
from app.models.finance import (
    FinancialLedgerEntry,
    NormalizedReportRow,
    RawReport,
    ReportReconciliation,
)
from app.models.inventory import InventoryLedgerEntry
from app.models.report import Marketplace, Report
from app.parsers.wb.semantics import SEMANTICS_VERSION


class WbPersistLayersMixin:
    """Layered idempotent inserts; mixed into WbFinancialPersistService."""

    db: AsyncSession
    user_id: UUID

    async def _persist_raw_report(
        self,
        *,
        report: Report,
        file_checksum: str,
        storage_uri: str,
        result: WbFinancialProcessResult,
    ) -> None:
        stmt = insert(RawReport).values(
            user_id=self.user_id,
            report_id=report.id,
            storage_uri=storage_uri,
            file_checksum=file_checksum,
            parser_name=result.parser_name,
            parser_version=result.parser_version,
            row_count=result.row_count,
            ingest_metadata={"marketplace": Marketplace.WILDBERRIES.value},
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["report_id"])
        await self.db.execute(stmt)

    async def _persist_normalized_rows(
        self,
        *,
        report_id: UUID,
        result: WbFinancialProcessResult,
    ) -> None:
        if not result.normalized_rows:
            return
        values = [
            {
                "user_id": self.user_id,
                "report_id": report_id,
                "source_row_id": row.source_row_id,
                "source_row_index": row.source_row_index,
                "operation_date": row.operation_date,
                "sku": row.sku,
                "nm_id": row.nm_id,
                "semantics_version": SEMANTICS_VERSION,
                "canonical_payload": serialize_payload(row.canonical),
                "raw_payload": row.raw,
            }
            for row in result.normalized_rows
        ]
        stmt = insert(NormalizedReportRow).on_conflict_do_nothing(
            constraint="uq_normalized_report_source_row"
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(stmt, batch)

    async def _persist_ledger(self, *, report_id: UUID, result: WbFinancialProcessResult) -> None:
        if not result.ledger_entries:
            return
        values = [
            {
                "user_id": self.user_id,
                "report_id": report_id,
                "operation_date": entry.operation_date,
                "sku": entry.sku,
                "nm_id": entry.nm_id,
                "operation_type": entry.operation_type,
                "amount": entry.amount,
                "currency": entry.currency,
                "source_row_id": entry.source_row_id,
                "entry_metadata": entry.entry_metadata,
            }
            for entry in result.ledger_entries
        ]
        stmt = insert(FinancialLedgerEntry).on_conflict_do_nothing(
            constraint="uq_ledger_report_source_row"
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(stmt, batch)

    async def _persist_inventory_ledger(
        self,
        *,
        report_id: UUID,
        result: WbFinancialProcessResult,
    ) -> None:
        if not result.inventory_movements:
            return
        values = [
            {
                "user_id": self.user_id,
                "report_id": report_id,
                "operation_date": movement.operation_date,
                "sku": movement.sku,
                "nm_id": movement.nm_id,
                "warehouse_name": movement.warehouse_name,
                "operation_type": movement.operation_type,
                "quantity_delta": movement.quantity_delta,
                "cost_per_unit": movement.cost_per_unit,
                "sale_price_per_unit": movement.sale_price_per_unit,
                "total_cost_delta": movement.total_cost_delta,
                "total_sale_delta": movement.total_sale_delta,
                "source_row_id": movement.source_row_id,
                "semantics_version": movement.semantics_version,
                "canonical_payload": serialize_payload(movement.canonical_payload),
                "raw_payload": movement.raw_payload,
            }
            for movement in result.inventory_movements
        ]
        stmt = insert(InventoryLedgerEntry).on_conflict_do_nothing(
            constraint="uq_inventory_ledger_report_source_operation"
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(stmt, batch)

    async def _persist_phase1_chunk(
        self,
        *,
        report_id: UUID,
        chunk: WbProcessChunk,
    ) -> None:
        if chunk.normalized_rows:
            norm_values = [
                {
                    "user_id": self.user_id,
                    "report_id": report_id,
                    "source_row_id": row.source_row_id,
                    "source_row_index": row.source_row_index,
                    "operation_date": row.operation_date,
                    "sku": row.sku,
                    "nm_id": row.nm_id,
                    "semantics_version": SEMANTICS_VERSION,
                    "canonical_payload": serialize_payload(row.canonical),
                    "raw_payload": row.raw,
                }
                for row in chunk.normalized_rows
            ]
            norm_stmt = insert(NormalizedReportRow).on_conflict_do_nothing(
                constraint="uq_normalized_report_source_row"
            )
            for batch in iter_batches(norm_values, batch_size=INSERT_BATCH_SIZE):
                await self.db.execute(norm_stmt, batch)

        if chunk.ledger_entries:
            ledger_values = [
                {
                    "user_id": self.user_id,
                    "report_id": report_id,
                    "operation_date": entry.operation_date,
                    "sku": entry.sku,
                    "nm_id": entry.nm_id,
                    "operation_type": entry.operation_type,
                    "amount": entry.amount,
                    "currency": entry.currency,
                    "source_row_id": entry.source_row_id,
                    "entry_metadata": entry.entry_metadata,
                }
                for entry in chunk.ledger_entries
            ]
            ledger_stmt = insert(FinancialLedgerEntry).on_conflict_do_nothing(
                constraint="uq_ledger_report_source_row"
            )
            for batch in iter_batches(ledger_values, batch_size=INSERT_BATCH_SIZE):
                await self.db.execute(ledger_stmt, batch)

        if chunk.inventory_movements:
            inv_values = [
                {
                    "user_id": self.user_id,
                    "report_id": report_id,
                    "operation_date": movement.operation_date,
                    "sku": movement.sku,
                    "nm_id": movement.nm_id,
                    "warehouse_name": movement.warehouse_name,
                    "operation_type": movement.operation_type,
                    "quantity_delta": movement.quantity_delta,
                    "cost_per_unit": movement.cost_per_unit,
                    "sale_price_per_unit": movement.sale_price_per_unit,
                    "total_cost_delta": movement.total_cost_delta,
                    "total_sale_delta": movement.total_sale_delta,
                    "source_row_id": movement.source_row_id,
                    "semantics_version": movement.semantics_version,
                    "canonical_payload": serialize_payload(movement.canonical_payload),
                    "raw_payload": movement.raw_payload,
                }
                for movement in chunk.inventory_movements
            ]
            inv_stmt = insert(InventoryLedgerEntry).on_conflict_do_nothing(
                constraint="uq_inventory_ledger_report_source_operation"
            )
            for batch in iter_batches(inv_values, batch_size=INSERT_BATCH_SIZE):
                await self.db.execute(inv_stmt, batch)

    async def _persist_reconciliation(
        self,
        *,
        report_id: UUID,
        result: WbFinancialProcessResult,
    ) -> None:
        rec = result.reconciliation
        stmt = insert(ReportReconciliation).values(
            user_id=self.user_id,
            report_id=report_id,
            gross_revenue=rec.gross_revenue,
            net_revenue=rec.net_revenue,
            wb_commissions=rec.wb_commissions,
            logistics=rec.logistics,
            deductions=rec.deductions,
            returns_amount=rec.returns_amount,
            expected_payout=rec.expected_payout,
            actual_payout=rec.actual_payout,
            difference=rec.difference,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["report_id"],
            set_={
                "gross_revenue": rec.gross_revenue,
                "net_revenue": rec.net_revenue,
                "wb_commissions": rec.wb_commissions,
                "logistics": rec.logistics,
                "deductions": rec.deductions,
                "returns_amount": rec.returns_amount,
                "expected_payout": rec.expected_payout,
                "actual_payout": rec.actual_payout,
                "difference": rec.difference,
            },
        )
        await self.db.execute(stmt)

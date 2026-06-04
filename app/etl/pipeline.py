from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.domain.inventory.analytics_payload import extend_analytics_payload
from app.etl.anomaly_persist import EtlAnomalyPersistService
from app.etl.loaders import dataframe_to_raw_records, load_file_to_dataframe
from app.etl.pipeline_analytics import LegacyAnalyticsBuilder
from app.etl.processors import (
    aggregate_kpis_placeholder,
    extract_costs_placeholder,
    extract_products_placeholder,
    normalize_marketplace_data,
)
from app.etl.types import AnalyticsPayload, ETLResult
from app.etl.validators import validate_dataframe_values
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.etl.wb.types import WbFinancialProcessResult
from app.models.ai_insights import AIInsight, InsightStatus
from app.models.report import Marketplace, Report, ReportType
from app.services.report_service import ReportService


class ETLPipeline:
    """
    Simplified ETL flow:
    1. Load raw file → pandas
    2. Save raw snapshot (JSONB on report)
    3. Placeholder transforms
    4. Placeholder KPI aggregation
    5. Prepare ai_insights context slot using clean domain layer and DTO contracts
    """

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def run(
        self,
        report: Report,
        filename: str,
        content: bytes,
        report_service: ReportService,
    ) -> Report:
        result = self.process_content(
            report_id=report.id,
            report_created_at=report.created_at,
            filename=filename,
            content=content,
            marketplace=report.marketplace,
            report_type=report.report_type,
        )
        return await self.persist_result(report, result, report_service)

    @staticmethod
    def process_content(
        *,
        report_id: UUID,
        report_created_at: datetime,
        filename: str,
        content: bytes,
        marketplace: Marketplace,
        report_type: ReportType,
    ) -> ETLResult:
        """
        Phase 2: CPU/data work outside DB transactions and without a DB session.
        This method may do pandas parsing, validation and aggregation safely.
        """
        if marketplace == Marketplace.WILDBERRIES:
            wb_result = WbFinancialProcessor.process(
                report_id=report_id,
                report_created_at=report_created_at,
                filename=filename,
                content=content,
            )
            return ETLResult(
                raw_data=wb_result.raw_snapshot,
                row_count=wb_result.row_count,
                analytics_payload=wb_result.analytics_payload,
                wb_financial=wb_result,
            )

        df = load_file_to_dataframe(filename, content)
        validate_dataframe_values(df)
        raw_data = dataframe_to_raw_records(df)
        df = normalize_marketplace_data(df, marketplace)

        if report_type == ReportType.COSTS or marketplace == Marketplace.COSTS:
            extract_costs_placeholder(df)
        else:
            extract_products_placeholder(df, marketplace)
            aggregate_kpis_placeholder(df, marketplace)

        analytics_payload = LegacyAnalyticsBuilder.build_analytics_payload(
            report_id=report_id,
            report_created_at=report_created_at,
            marketplace=marketplace,
            df=df,
        )
        return ETLResult(
            raw_data=raw_data,  # type: ignore[arg-type]
            row_count=int(raw_data["row_count"]),
            analytics_payload=analytics_payload,
            wb_financial=None,
        )

    @staticmethod
    def build_analytics_payload(
        *,
        report_id: UUID,
        report_created_at: datetime,
        marketplace: Marketplace,
        df,
    ) -> AnalyticsPayload:
        """Backward-compatible delegate to LegacyAnalyticsBuilder."""
        return LegacyAnalyticsBuilder.build_analytics_payload(
            report_id=report_id,
            report_created_at=report_created_at,
            marketplace=marketplace,
            df=df,
        )

    async def persist_result(
        self,
        report: Report,
        result: ETLResult,
        report_service: ReportService,
        *,
        job_id: UUID | None = None,
        in_transaction: bool = False,
    ) -> Report:
        """Atomic persist phase: domain data + idempotent AI slot."""
        if isinstance(result.wb_financial, WbFinancialProcessResult):
            persist_service = WbFinancialPersistService(self.db, self.user_id)
            costs = await persist_service.load_cost_snapshots(self.db, self.user_id)
            wb_enriched = WbFinancialProcessor.enrich_with_costs(result.wb_financial, costs)
            if in_transaction:
                loss_analytics = await persist_service.persist(
                    report=report,
                    file_checksum=report.file_checksum or "",
                    storage_uri=report.file_path or "",
                    result=wb_enriched,
                    costs_by_sku=costs,
                )
            else:
                async with TenantSession.transaction(self.db, self.user_id):
                    loss_analytics = await persist_service.persist(
                        report=report,
                        file_checksum=report.file_checksum or "",
                        storage_uri=report.file_path or "",
                        result=wb_enriched,
                        costs_by_sku=costs,
                    )
            analytics_payload = extend_analytics_payload(
                dict(wb_enriched.analytics_payload),
                loss_analytics=loss_analytics,
            )
            await self._prepare_ai_context_idempotent(
                report,
                analytics_payload,
                job_id=job_id,
                in_transaction=in_transaction,
            )
            await self._persist_etl_anomalies_best_effort(
                wb_enriched.etl_anomalies,
                report_id=report.id,
                in_transaction=in_transaction,
            )
            return await report_service.persist_business_result(
                report,
                raw_data=dict(wb_enriched.raw_snapshot),
                row_count=wb_enriched.row_count,
                in_transaction=in_transaction,
            )

        await self._prepare_ai_context_idempotent(
            report,
            result.analytics_payload,
            job_id=job_id,
            in_transaction=in_transaction,
        )
        return await report_service.persist_business_result(
            report,
            raw_data=dict(result.raw_data),
            row_count=result.row_count,
            in_transaction=in_transaction,
        )

    async def _persist_etl_anomalies_best_effort(
        self,
        anomalies: tuple,
        *,
        report_id: UUID,
        in_transaction: bool,  # noqa: ARG002
    ) -> None:
        if not anomalies:
            return
        try:
            async with TenantSession.transaction(self.db, self.user_id):
                await EtlAnomalyPersistService(self.db, self.user_id).persist_best_effort(
                    list(anomalies)
                )
        except Exception:
            pass

    async def _prepare_ai_context_idempotent(
        self,
        report: Report,
        analytics_payload: AnalyticsPayload,
        *,
        job_id: UUID | None = None,
        in_transaction: bool = False,
    ) -> None:
        """Create AI insight once per report/job (retry-safe)."""
        report_key = str(report.id)
        existing = await self.db.execute(
            select(AIInsight).where(
                AIInsight.user_id == self.user_id,
                AIInsight.insight_type == "report_summary",
            )
        )
        for row in existing.scalars():
            payload = row.context_payload or {}
            if str(payload.get("report_id")) == report_key:
                return

        payload = dict(analytics_payload)
        if job_id is not None:
            payload["job_id"] = str(job_id)

        insight = AIInsight(
            user_id=self.user_id,
            insight_type="report_summary",
            status=InsightStatus.PENDING,
            title=f"Analysis pending: {report.original_filename}",
            context_payload=payload,
        )
        self.db.add(insight)
        if in_transaction:
            await self.db.flush()
        else:
            async with TenantSession.transaction(self.db, self.user_id):
                await self.db.flush()

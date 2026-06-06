from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.etl.wb.persist import WbFinancialPersistService
from app.models.cost_history import CostHistory
from app.models.product import Product
from app.models.user import User
from app.parsers.wb.base import normalize_header, parse_decimal
from app.schemas.cost_import import (
    CostImportIssue,
    CostImportPreviewResponse,
    CostImportPreviewRow,
    CostImportResultResponse,
)
from app.services.base import TenantScopedService

_COST_IMPORT_ALIASES: dict[str, tuple[str, ...]] = {
    "internal_sku": ("internal_sku", "sku", "артикул", "артикул поставщика"),
    "effective_from": ("effective_from", "date", "дата", "дата начала"),
    "product_cost": ("product_cost", "cost", "себестоимость", "product cost"),
    "packaging_cost": ("packaging_cost", "упаковка", "packaging"),
    "inbound_logistics_cost": (
        "inbound_logistics_cost",
        "logistics",
        "логистика",
        "inbound logistics",
    ),
    "additional_cost": ("additional_cost", "доп", "additional"),
    "currency": ("currency", "валюта"),
    "comment": ("comment", "комментарий"),
}


class CostService(TenantScopedService):
    def __init__(self, db: AsyncSession, user: User):
        super().__init__(db, user_id=user.id)
        self.user = user

    @staticmethod
    def _parse_import_date(raw: object) -> date | None:
        """Normalize Excel/pandas date cells to plain date for strict API models."""
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return None
        if isinstance(raw, datetime):
            return raw.date()
        if type(raw) is date:
            return raw
        parsed = pd.to_datetime(raw, errors="coerce")
        if pd.isna(parsed):
            return None
        if isinstance(parsed, datetime):
            return parsed.date()
        if isinstance(parsed, date):
            return parsed
        return None

    @staticmethod
    def _load_cost_import_dataframe(filename: str, content: bytes) -> pd.DataFrame:
        """Load cost CSV/Excel without WB report header heuristics."""
        lower = filename.lower()
        buffer = BytesIO(content)
        try:
            if lower.endswith(".csv"):
                return pd.read_csv(buffer)
            if lower.endswith((".xlsx", ".xls")):
                return pd.read_excel(buffer)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Не удалось прочитать файл: {exc}",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат файла: {filename}",
        )

    @staticmethod
    def _cell_text(value: object) -> str | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        return text or None

    async def _refresh_financial_projections(self) -> None:
        async with self._rls_transaction():
            await WbFinancialPersistService(self.db, self.user.id).rebuild_all_financial_projections()

    async def create_cost(
        self,
        *,
        internal_sku: str,
        effective_from: date,
        product_cost: Decimal,
        packaging_cost: Decimal = Decimal("0"),
        inbound_logistics_cost: Decimal = Decimal("0"),
        additional_cost: Decimal = Decimal("0"),
        currency: str = "RUB",
        comment: str | None = None,
    ) -> CostHistory:
        total = product_cost + packaging_cost + inbound_logistics_cost + additional_cost
        row = CostHistory(
            user_id=self.user.id,
            internal_sku=internal_sku,
            product_cost=product_cost,
            packaging_cost=packaging_cost,
            inbound_logistics_cost=inbound_logistics_cost,
            additional_cost=additional_cost,
            cost=total,
            currency=currency,
            effective_from=effective_from,
            comment=comment,
        )
        async with self._rls_transaction():
            self.db.add(row)
            await self.db.flush()
            await self.db.refresh(row)
        await self._refresh_financial_projections()
        return row

    async def list_costs(
        self,
        *,
        sku: str | None = None,
        as_of: date | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
    ) -> list[CostHistory]:
        query = select(CostHistory).order_by(
            CostHistory.internal_sku.asc(),
            CostHistory.effective_from.desc(),
        )
        if sku:
            query = query.where(CostHistory.internal_sku == sku)
        if effective_from is not None:
            query = query.where(CostHistory.effective_from >= effective_from)
        if effective_to is not None:
            query = query.where(CostHistory.effective_from <= effective_to)
        async with self._rls_transaction():
            result = await self.db.execute(query)
        rows = list(result.scalars().all())
        if as_of is None:
            return rows
        return self.filter_costs_as_of(rows, as_of)

    @staticmethod
    def filter_costs_as_of(rows: list[CostHistory], as_of: date) -> list[CostHistory]:
        latest_by_sku: dict[str, CostHistory] = {}
        for row in rows:
            if row.effective_from > as_of:
                continue
            if row.effective_to is not None and row.effective_to < as_of:
                continue
            prev = latest_by_sku.get(row.internal_sku)
            if prev is None or row.effective_from > prev.effective_from:
                latest_by_sku[row.internal_sku] = row
        return sorted(
            latest_by_sku.values(),
            key=lambda r: (r.internal_sku, r.effective_from),
            reverse=True,
        )

    async def update_cost(
        self,
        cost_id: UUID,
        *,
        product_cost: Decimal | None = None,
        packaging_cost: Decimal | None = None,
        inbound_logistics_cost: Decimal | None = None,
        additional_cost: Decimal | None = None,
        currency: str | None = None,
        comment: str | None = None,
    ) -> CostHistory:
        row = await self.get_cost(cost_id)
        if product_cost is not None:
            row.product_cost = product_cost
        if packaging_cost is not None:
            row.packaging_cost = packaging_cost
        if inbound_logistics_cost is not None:
            row.inbound_logistics_cost = inbound_logistics_cost
        if additional_cost is not None:
            row.additional_cost = additional_cost
        if currency is not None:
            row.currency = currency
        if comment is not None:
            row.comment = comment
        row.cost = (
            row.product_cost
            + row.packaging_cost
            + row.inbound_logistics_cost
            + row.additional_cost
        )
        async with self._rls_transaction():
            self.db.add(row)
            await self.db.flush()
            await self.db.refresh(row)
        await self._refresh_financial_projections()
        return row

    async def get_cost(self, cost_id: UUID) -> CostHistory:
        async with self._rls_transaction():
            result = await self.db.execute(select(CostHistory).where(CostHistory.id == cost_id))
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cost record not found",
            )
        return row

    @staticmethod
    def _resolve_cost_columns(columns: list[str]) -> dict[str, str | None]:
        normalized = {normalize_header(column): column for column in columns}
        resolved: dict[str, str | None] = {}
        for field, aliases in _COST_IMPORT_ALIASES.items():
            match = None
            for alias in aliases:
                alias_norm = normalize_header(alias)
                for header_norm, original in normalized.items():
                    if alias_norm == header_norm or alias_norm in header_norm:
                        match = original
                        break
                if match:
                    break
            resolved[field] = match
        return resolved

    def _preview_rows(
        self,
        *,
        df: pd.DataFrame,
        column_map: dict[str, str | None],
        max_rows: int = 20,
    ) -> list[CostImportPreviewRow]:
        rows: list[CostImportPreviewRow] = []
        for index, row in df.head(max_rows).iterrows():
            sku_col = column_map.get("internal_sku")
            date_col = column_map.get("effective_from")
            product_col = column_map.get("product_cost")

            sku_value = self._cell_text(row.get(sku_col)) if sku_col else None

            eff = self._parse_import_date(row.get(date_col)) if date_col else None

            product_cost = None
            if product_col:
                product_cost = parse_decimal(row.get(product_col))

            packaging = parse_decimal(row.get(column_map.get("packaging_cost"))) if column_map.get("packaging_cost") else None
            inbound = parse_decimal(row.get(column_map.get("inbound_logistics_cost"))) if column_map.get("inbound_logistics_cost") else None
            additional = parse_decimal(row.get(column_map.get("additional_cost"))) if column_map.get("additional_cost") else None

            currency = None
            currency_col = column_map.get("currency")
            if currency_col:
                currency = (self._cell_text(row.get(currency_col)) or "")[:3] or None

            comment = self._cell_text(row.get(comment_col)) if (comment_col := column_map.get("comment")) else None

            total = None
            if product_cost is not None:
                total = product_cost + (packaging or Decimal("0")) + (inbound or Decimal("0")) + (additional or Decimal("0"))

            rows.append(
                CostImportPreviewRow(
                    row_index=int(index),
                    internal_sku=sku_value,
                    effective_from=eff,
                    product_cost=product_cost,
                    packaging_cost=packaging,
                    inbound_logistics_cost=inbound,
                    additional_cost=additional,
                    currency=currency,
                    comment=comment,
                    total_cost=total,
                )
            )
        return rows

    async def preview_import(self, *, filename: str, content: bytes) -> CostImportPreviewResponse:
        df = self._load_cost_import_dataframe(filename, content)
        column_map = self._resolve_cost_columns(list(df.columns))

        issues: list[CostImportIssue] = []
        if not column_map.get("internal_sku") or not column_map.get("effective_from"):
            issues.append(
                CostImportIssue(
                    severity="error",
                    code="missing_required_columns",
                    message="Файл должен содержать колонки SKU и дата начала (effective_from).",
                )
            )
        if not column_map.get("product_cost"):
            issues.append(
                CostImportIssue(
                    severity="error",
                    code="missing_product_cost",
                    message="Файл должен содержать колонку «себестоимость» (product_cost).",
                )
            )

        preview_rows = self._preview_rows(df=df, column_map=column_map, max_rows=20)
        return CostImportPreviewResponse(
            detected_columns=column_map,
            total_rows=int(len(df)),
            preview_rows=preview_rows,
            issues=issues,
        )

    async def bulk_import_v2(self, *, filename: str, content: bytes) -> CostImportResultResponse:
        df = self._load_cost_import_dataframe(filename, content)
        column_map = self._resolve_cost_columns(list(df.columns))
        if not column_map.get("internal_sku") or not column_map.get("effective_from"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл должен содержать колонки SKU и effective_from (дата начала).",
            )
        if not column_map.get("product_cost"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Файл должен содержать колонку «себестоимость» (product_cost).",
            )

        sku_col = column_map["internal_sku"]
        date_col = column_map["effective_from"]
        product_col = column_map["product_cost"]
        assert sku_col and date_col and product_col

        issues: list[CostImportIssue] = []
        imported_rows = 0
        skipped_rows = 0
        imported_skus: set[str] = set()

        # Preload known internal_sku (warning only)
        candidate_skus = {
            str(v).strip()
            for v in df[sku_col].fillna("").astype(str).tolist()
            if str(v).strip()
        }
        known_internal_skus: set[str] = set()
        async with self._rls_transaction():
            if candidate_skus:
                result = await self.db.execute(
                    select(Product.internal_sku)
                    .where(Product.internal_sku.is_not(None))
                    .where(Product.internal_sku.in_(candidate_skus))
                )
                known_internal_skus = {str(v) for v in result.scalars().all() if v}

        invalid_sku_count = 0

        async with self._rls_transaction():
            for index, row in df.iterrows():
                sku_value = str(row[sku_col]).strip()
                if not sku_value:
                    skipped_rows += 1
                    issues.append(
                        CostImportIssue(
                            severity="warning",
                            code="empty_sku",
                            message="Пустой SKU — строка пропущена.",
                            row_index=int(index),
                        )
                    )
                    continue

                effective_from = self._parse_import_date(row[date_col])
                if effective_from is None:
                    skipped_rows += 1
                    issues.append(
                        CostImportIssue(
                            severity="warning",
                            code="bad_date",
                            message="Не удалось распарсить дату — строка пропущена.",
                            row_index=int(index),
                        )
                    )
                    continue

                product_cost = parse_decimal(row[product_col])
                if product_cost is None or product_cost <= Decimal("0"):
                    skipped_rows += 1
                    issues.append(
                        CostImportIssue(
                            severity="warning",
                            code="bad_cost",
                            message="Себестоимость пустая/некорректная (<=0) — строка пропущена.",
                            row_index=int(index),
                        )
                    )
                    continue

                if known_internal_skus and sku_value not in known_internal_skus:
                    invalid_sku_count += 1
                    issues.append(
                        CostImportIssue(
                            severity="warning",
                            code="unknown_sku",
                            message="SKU не найден в каталоге. Проверьте маппинг/название — себестоимость всё равно импортирована.",
                            row_index=int(index),
                        )
                    )

                packaging = parse_decimal(row.get(column_map["packaging_cost"])) or Decimal("0")
                inbound_col = column_map["inbound_logistics_cost"]
                inbound = parse_decimal(row.get(inbound_col)) or Decimal("0")
                additional = parse_decimal(row.get(column_map["additional_cost"])) or Decimal("0")
                currency_col = column_map.get("currency")
                currency = "RUB"
                if currency_col and row.get(currency_col) is not None:
                    currency = str(row[currency_col]).strip()[:3] or "RUB"
                comment_col = column_map.get("comment")
                comment = None
                if comment_col and row.get(comment_col) is not None:
                    comment = str(row[comment_col]).strip() or None

                total = product_cost + packaging + inbound + additional

                # Duplicate detection: same SKU + effective_from + total cost already exists
                existing = await self.db.execute(
                    select(CostHistory)
                    .where(CostHistory.internal_sku == sku_value)
                    .where(CostHistory.effective_from == effective_from)
                    .order_by(CostHistory.created_at.desc())
                    .limit(1)
                )
                last = existing.scalar_one_or_none()
                if last is not None and last.cost == total and last.currency == currency:
                    skipped_rows += 1
                    issues.append(
                        CostImportIssue(
                            severity="warning",
                            code="duplicate",
                            message="Дубликат (SKU + дата + сумма) — строка пропущена.",
                            row_index=int(index),
                        )
                    )
                    continue

                cost_row = CostHistory(
                    user_id=self.user.id,
                    internal_sku=sku_value,
                    product_cost=product_cost,
                    packaging_cost=packaging,
                    inbound_logistics_cost=inbound,
                    additional_cost=additional,
                    cost=total,
                    currency=currency,
                    effective_from=effective_from,
                    comment=comment,
                )
                self.db.add(cost_row)
                imported_rows += 1
                imported_skus.add(sku_value)

            await self.db.flush()

        await self._refresh_financial_projections()
        return CostImportResultResponse(
            detected_columns=column_map,
            total_rows=int(len(df)),
            imported_rows=imported_rows,
            skipped_rows=skipped_rows,
            imported_distinct_skus=len(imported_skus),
            invalid_sku_count=invalid_sku_count,
            issues=issues[:200],
        )

    async def bulk_import(self, *, filename: str, content: bytes) -> list[CostHistory]:
        df = self._load_cost_import_dataframe(filename, content)
        column_map = self._resolve_cost_columns(list(df.columns))
        if not column_map.get("internal_sku") or not column_map.get("effective_from"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import file must include SKU and effective_from columns",
            )
        if not column_map.get("product_cost"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import file must include product_cost column",
            )

        created: list[CostHistory] = []
        async with self._rls_transaction():
            for index, row in df.iterrows():
                sku_col = column_map["internal_sku"]
                date_col = column_map["effective_from"]
                product_col = column_map["product_cost"]
                assert sku_col and date_col and product_col

                sku_value = str(row[sku_col]).strip()
                if not sku_value:
                    continue

                effective_from = self._parse_import_date(row[date_col])
                if effective_from is None:
                    continue

                product_cost = parse_decimal(row[product_col])
                if product_cost is None or product_cost <= Decimal("0"):
                    continue

                packaging = parse_decimal(row.get(column_map["packaging_cost"])) or Decimal("0")
                inbound_col = column_map["inbound_logistics_cost"]
                inbound = parse_decimal(row.get(inbound_col)) or Decimal("0")
                additional = parse_decimal(row.get(column_map["additional_cost"])) or Decimal("0")
                currency_col = column_map.get("currency")
                currency = "RUB"
                if currency_col and row.get(currency_col) is not None:
                    currency = str(row[currency_col]).strip()[:3] or "RUB"
                comment_col = column_map.get("comment")
                comment = None
                if comment_col and row.get(comment_col) is not None:
                    comment = str(row[comment_col]).strip() or None

                total = product_cost + packaging + inbound + additional
                cost_row = CostHistory(
                    user_id=self.user.id,
                    internal_sku=sku_value,
                    product_cost=product_cost,
                    packaging_cost=packaging,
                    inbound_logistics_cost=inbound,
                    additional_cost=additional,
                    cost=total,
                    currency=currency,
                    effective_from=effective_from,
                    comment=comment,
                )
                self.db.add(cost_row)
                created.append(cost_row)
                _ = index

            await self.db.flush()
            for row in created:
                await self.db.refresh(row)
        return created

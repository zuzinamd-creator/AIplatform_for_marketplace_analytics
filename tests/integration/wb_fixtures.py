"""Deterministic WB CSV bytes for integration tests (comma-delimited for pandas read_csv)."""

from __future__ import annotations

# Comma-separated: default pd.read_csv delimiter; matches realization v2 header signatures.
_WB_SALE_ROW_TEMPLATE = (
    "Дата продажи,Артикул поставщика,Тип операции,Кол-во,Цена розничная,"
    "К перечислению,Склад,Комиссия\n"
    "2026-01-15,{sku},Продажа,2,1000,800,{warehouse},-100\n"
)


def wb_sale_csv(*, sku: str, warehouse: str = "Коледино") -> bytes:
    return _WB_SALE_ROW_TEMPLATE.format(sku=sku, warehouse=warehouse).encode("utf-8")

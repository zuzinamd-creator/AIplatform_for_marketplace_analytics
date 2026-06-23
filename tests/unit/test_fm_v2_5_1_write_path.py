from decimal import Decimal

from app.parsers.wb.base import resolve_column_map
from app.parsers.wb.rehydrate import canonical_from_raw_payload

PILOT_HEADERS = [
    "Дата продажи",
    "Артикул поставщика",
    "Код номенклатуры",
    "Обоснование для оплаты",
    "Цена розничная",
    "Вайлдберриз реализовал Товар (Пр)",
    "Вознаграждение Вайлдберриз (ВВ), без НДС",
    "Компенсация платёжных услуг/Комиссия за интеграцию платёжных сервисов",
    "Компенсация скидки по программе лояльности",
    "К перечислению Продавцу за реализованный Товар",
    "Количество возврата",
    "Возмещение за выдачу и возврат товаров на ПВЗ",
    "Услуги по доставке товара покупателю",
]


def test_resolve_wb_realized_column() -> None:
    resolved = resolve_column_map(PILOT_HEADERS)
    assert resolved["wb_realized_amount"] == "Вайлдберриз реализовал Товар (Пр)"
    assert resolved["payout"] == "К перечислению Продавцу за реализованный Товар"
    assert resolved["wb_realized_amount"] != resolved["payout"]


def test_resolve_pic_not_commission() -> None:
    resolved = resolve_column_map(PILOT_HEADERS)
    assert (
        resolved["payment_integration_compensation"]
        == "Компенсация платёжных услуг/Комиссия за интеграцию платёжных сервисов"
    )
    assert resolved["commission"] == "Вознаграждение Вайлдберриз (ВВ), без НДС"
    assert resolved["payment_integration_compensation"] != resolved["commission"]


def test_resolve_return_wb_not_qty() -> None:
    resolved = resolve_column_map(PILOT_HEADERS)
    assert resolved["return_wb"] == "Вайлдберриз реализовал Товар (Пр)"
    assert resolved["return_amount"] == "Количество возврата"
    assert resolved["return_wb"] != resolved["return_amount"]


def test_rehydrate_pilot_row() -> None:
    raw = {
        "Дата продажи": "2026-05-10",
        "Артикул поставщика": "SKU-PILOT",
        "Вайлдберриз реализовал Товар (Пр)": "2562.00",
        "Компенсация платёжных услуг/Комиссия за интеграцию платёжных сервисов": "8.31",
        "Компенсация скидки по программе лояльности": "12.50",
        "Количество возврата": "1",
        "К перечислению Продавцу за реализованный Товар": "2400.00",
        "Вознаграждение Вайлдберриз (ВВ), без НДС": "120.00",
    }
    canonical = canonical_from_raw_payload(raw)
    assert canonical["wb_realized_amount"] == Decimal("2562.00")
    assert canonical["payment_integration_compensation"] == Decimal("8.31")
    assert canonical["loyalty_compensation"] == Decimal("12.50")
    assert canonical["return_wb"] == Decimal("2562.00")
    assert canonical["return_amount"] == 1
    assert canonical["payout"] == Decimal("2400.00")
    assert canonical["commission"] == Decimal("120.00")

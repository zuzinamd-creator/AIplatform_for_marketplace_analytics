# Inventory Economics UI (складская экономика)

Цель: показать продавцу **оборот**, **замороженный капитал**, **медленные товары** и **мертвые остатки** в понятной ежедневной форме.

Ограничения: без прогнозного ML, только детерминированные расчеты на governed данных (RLS).

## Маршруты (frontend)

- `/app/economics/inventory` — “Склад и оборот”

## API (backend)

- `GET /api/v1/analytics/inventory-economics`
  - query: `marketplace`, `start`, `end`, `limit`, `q`, `semantics_version`
- `GET /api/v1/analytics/inventory-economics/slow-movers`
  - query: `marketplace`, `start`, `end`, `threshold_days`, `limit`, `semantics_version`
- `GET /api/v1/analytics/inventory-economics/dead-stock`
  - query: `marketplace`, `start`, `end`, `threshold_days`, `limit`, `semantics_version`

## Метрики и смысл

- **Оборот (раз)**: `sold_units / avg_stock_units`
- **Оборот (дней)**: `avg_stock_units / avg_daily_sold_units`
- **Замороженный капитал**: `stock_units * unit_cost` (best-effort; если себестоимость не задана — поле пустое)
- **Медленные товары**: `days_since_last_sale >= threshold_days` (по умолчанию 30)
- **Мертвые остатки**: `days_since_last_sale >= threshold_days` (по умолчанию 60)
- **Риск**:
  - `stockout`: низкий остаток при наличии продаж
  - `overstock`: много дней без продаж при положительном остатке

## Trust UX

- показываем `integrity` (полнота + предупреждения)
- в UI явно написано, что расчет замороженного капитала зависит от себестоимости


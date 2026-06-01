# Analytical transparency (seller trust UX)

Seller-facing transparency elements:

- "Данные проанализированы за период: X–Y"
- "Последнее обновление: …"
- "Полнота аналитики: N%"
- explicit integrity warnings (impossible KPI detection)
- clear notes when a metric is missing or limited by missing report types / costs

Primary data source for transparency:

- `GET /api/v1/analytics/coverage`
- KPI endpoints `freshness` + `integrity`


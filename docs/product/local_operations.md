# Локальная эксплуатация (ежедневно)

## Команда “с утра”

1. Поднять backend + worker (и при необходимости orchestrator).
2. Поднять frontend.
3. Проверить `/app/status`.
4. Открыть `/app/today` и выполнить top‑действия.

## Workflow‑персистентность

Действия продавца сохраняются как append‑only события:

- заметки
- напоминания
- done today / waiting for data / return later
- история изменения состояния рекомендаций (complete/dismiss/save/snooze)

API: `/api/v1/workflow/*`


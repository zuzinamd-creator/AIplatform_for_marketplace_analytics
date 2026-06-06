"""User-facing ETL error hints for failed reports."""

from __future__ import annotations

from app.models.job import EtlJob, JobStatus


def is_report_retryable(job: EtlJob | None) -> bool:
    if job is None:
        return False
    return job.status in (JobStatus.FAILED, JobStatus.DEAD_LETTER)


def user_facing_error_hint(*, last_error: str | None, job: EtlJob | None) -> str | None:
    if not last_error:
        return None
    lower = last_error.lower()
    if "closed transaction" in lower or "invalidrequesterror" in lower:
        return (
            "Ошибка сохранения данных на сервере после успешного разбора файла. "
            "Нажмите «Повторить обработку» — повторная попытка обычно решает проблему."
        )
    if "no data rows" in lower or "contains no data" in lower:
        return "Файл пустой или формат не распознан. Проверьте, что выбран детализированный отчёт WB (.xlsx)."
    if "lock timeout" in lower or "lock_timeout" in lower:
        return "Сервер был перегружен. Подождите 1–2 минуты и нажмите «Повторить обработку»."
    if "inventory rebuild busy" in lower:
        return "Параллельная пересборка склада. Повторите обработку через несколько минут."
    if job and job.status == JobStatus.DEAD_LETTER:
        return "Обработка исчерпала автоматические попытки. Нажмите «Повторить обработку» для ручного перезапуска."
    return None

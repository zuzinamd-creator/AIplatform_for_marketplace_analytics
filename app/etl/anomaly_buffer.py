"""In-memory ETL anomaly collection (no per-row DB writes during parsing)."""

from __future__ import annotations

from app.domain.etl.anomaly_draft import EtlAnomalyDraft


class EtlAnomalyBuffer:
    def __init__(self) -> None:
        self._items: list[EtlAnomalyDraft] = []

    def add(self, draft: EtlAnomalyDraft) -> None:
        self._items.append(draft)

    def extend(self, drafts: list[EtlAnomalyDraft]) -> None:
        self._items.extend(drafts)

    def __len__(self) -> int:
        return len(self._items)

    def drain(self) -> list[EtlAnomalyDraft]:
        items = list(self._items)
        self._items.clear()
        return items

    def peek(self) -> tuple[EtlAnomalyDraft, ...]:
        return tuple(self._items)

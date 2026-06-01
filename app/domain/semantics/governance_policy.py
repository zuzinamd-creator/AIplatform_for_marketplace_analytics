"""Semantics lifecycle policy (code defaults + optional DB overlay)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.domain.semantics.errors import UnsupportedSemanticsVersionError


class SemanticsLifecycleStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


@dataclass(frozen=True)
class SemanticsLifecycleRecord:
    version: str
    status: SemanticsLifecycleStatus
    supported_for_rebuild: bool
    supported_for_ingest: bool


# Code defaults mirror migration seed; DB row overrides when loaded into cache.
_BUILTIN: dict[str, SemanticsLifecycleRecord] = {
    "1.0": SemanticsLifecycleRecord(
        version="1.0",
        status=SemanticsLifecycleStatus.ACTIVE,
        supported_for_rebuild=True,
        supported_for_ingest=True,
    ),
}

_lifecycle_cache: dict[str, SemanticsLifecycleRecord] = dict(_BUILTIN)


def set_lifecycle_cache(records: dict[str, SemanticsLifecycleRecord]) -> None:
    global _lifecycle_cache
    merged = dict(_BUILTIN)
    merged.update(records)
    _lifecycle_cache = merged


def clear_lifecycle_cache() -> None:
    global _lifecycle_cache
    _lifecycle_cache = dict(_BUILTIN)


def get_lifecycle_record(version: str) -> SemanticsLifecycleRecord:
    record = _lifecycle_cache.get(version)
    if record is None:
        raise UnsupportedSemanticsVersionError(version)
    return record


def assert_ingest_allowed(version: str) -> None:
    from app.parsers.wb.semantics_registry import SEMANTICS_REGISTRY

    record = get_lifecycle_record(version)
    if not record.supported_for_ingest or record.status == SemanticsLifecycleStatus.DISABLED:
        raise UnsupportedSemanticsVersionError(version)
    if record.status == SemanticsLifecycleStatus.DEPRECATED:
        raise UnsupportedSemanticsVersionError(version)
    if version not in SEMANTICS_REGISTRY:
        raise UnsupportedSemanticsVersionError(version)


def assert_rebuild_allowed(version: str) -> None:
    from app.parsers.wb.semantics_registry import SEMANTICS_REGISTRY

    record = get_lifecycle_record(version)
    if not record.supported_for_rebuild or record.status == SemanticsLifecycleStatus.DISABLED:
        raise UnsupportedSemanticsVersionError(version)
    if version not in SEMANTICS_REGISTRY:
        raise UnsupportedSemanticsVersionError(version)

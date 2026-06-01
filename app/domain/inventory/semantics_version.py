from __future__ import annotations

from app.domain.inventory.errors import UnsupportedSemanticsVersionError


def require_semantics_version(version: str | None) -> str:
    if not version or not str(version).strip():
        raise UnsupportedSemanticsVersionError("<missing>")
    return str(version).strip()

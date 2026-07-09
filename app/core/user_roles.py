"""User role constants and helpers (Phase 9.2B — minimal admin foundation)."""

from __future__ import annotations

USER_ROLE_SELLER = "seller"
USER_ROLE_PLATFORM_ADMIN = "platform_admin"

VALID_USER_ROLES: frozenset[str] = frozenset({USER_ROLE_SELLER, USER_ROLE_PLATFORM_ADMIN})
DEFAULT_USER_ROLE = USER_ROLE_SELLER

PLATFORM_ADMIN_EMAIL = "margarita.zuzina@mail.ru"


def is_platform_admin(role: str) -> bool:
    return role == USER_ROLE_PLATFORM_ADMIN


def user_role_error(role: str) -> str | None:
    normalized = role.strip().lower()
    if normalized not in VALID_USER_ROLES:
        allowed = ", ".join(sorted(VALID_USER_ROLES))
        return f"role must be one of: {allowed} (got {role!r})"
    return None

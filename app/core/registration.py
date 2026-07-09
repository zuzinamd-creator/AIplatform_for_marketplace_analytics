"""Registration mode gate (Phase 9.1A — invite-only controlled onboarding)."""

from __future__ import annotations

from app.core.config import settings

VALID_REGISTRATION_MODES: frozenset[str] = frozenset({"open", "invite_only", "disabled"})
DEFAULT_REGISTRATION_MODE = "invite_only"
REGISTRATION_UNAVAILABLE_MESSAGE = "Registration is currently unavailable."
INVITE_REQUIRED_MESSAGE = "Valid invitation required."


def normalize_registration_mode(mode: str) -> str:
    return mode.strip().lower()


def registration_mode_error(mode: str) -> str | None:
    normalized = normalize_registration_mode(mode)
    if normalized not in VALID_REGISTRATION_MODES:
        allowed = ", ".join(sorted(VALID_REGISTRATION_MODES))
        return f"REGISTRATION_MODE must be one of: {allowed} (got {mode!r})"
    return None


def is_registration_open(mode: str | None = None) -> bool:
    normalized = normalize_registration_mode(mode or settings.registration_mode)
    return normalized == "open"


def is_invite_only_mode(mode: str | None = None) -> bool:
    normalized = normalize_registration_mode(mode or settings.registration_mode)
    return normalized == "invite_only"

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import settings


@dataclass(frozen=True)
class EnvironmentInfo:
    mode: str  # LOCAL_DEV | INTEGRATION | MAIN
    db_host: str
    db_name: str
    is_ephemeral: bool
    is_production_like: bool


def _parse_db(url: str) -> tuple[str, str]:
    parsed = urlparse(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    host = parsed.hostname or ""
    db = (parsed.path or "").lstrip("/") or ""
    return host, db


def is_supabase_direct_host(host: str) -> bool:
    """Supabase direct Postgres: db.<project-ref>.supabase.co"""
    h = host.lower()
    return h.startswith("db.") and h.endswith(".supabase.co")


def is_supabase_pooler_host(host: str) -> bool:
    return "pooler.supabase.com" in host.lower()


def is_supabase_host(host: str) -> bool:
    h = host.lower()
    return is_supabase_direct_host(h) or is_supabase_pooler_host(h)


def detect_environment() -> EnvironmentInfo:
    mode = (settings.environment_mode or "LOCAL_DEV").upper().strip()
    host, db = _parse_db(settings.database_url)

    ephemeral_hosts = {
        "",
        "localhost",
        "127.0.0.1",
        "::1",
        "postgres",
        "postgres_integration",
    }
    is_ephemeral = host in ephemeral_hosts and not is_supabase_host(host)

    # MAIN is expected to be persistent and production-like (Supabase Postgres).
    is_production_like = mode == "MAIN" and not is_ephemeral

    return EnvironmentInfo(
        mode=mode,
        db_host=host,
        db_name=db,
        is_ephemeral=is_ephemeral,
        is_production_like=is_production_like,
    )


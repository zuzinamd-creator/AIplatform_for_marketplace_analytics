"""Startup environment and consistency validation."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.environment import (
    detect_environment,
    is_supabase_direct_host,
    is_supabase_pooler_host,
)
from app.core.observability import get_logger

logger = get_logger("startup_validation")


@dataclass(frozen=True)
class StartupValidationReport:
    ok: bool
    warnings: tuple[str, ...]
    errors: tuple[str, ...]


def validate_environment() -> StartupValidationReport:
    warnings: list[str] = []
    errors: list[str] = []

    env = detect_environment()
    logger.info(
        "environment_detected",
        extra={
            "environment_mode": env.mode,
            "db_host": env.db_host,
            "db_name": env.db_name,
            "is_ephemeral": env.is_ephemeral,
            "is_production_like": env.is_production_like,
        },
    )

    if env.mode == "MAIN":
        if env.is_ephemeral:
            errors.append(
                "ENVIRONMENT_MODE=MAIN requires a persistent cloud database (e.g. Supabase Postgres), not localhost/docker."
            )
        url = settings.database_url.lower()
        if "ssl=require" not in url and "ssl=true" not in url and "sslmode=require" not in url:
            errors.append(
                "MAIN mode requires SSL for DATABASE_URL (add ?ssl=require for Supabase/asyncpg)."
            )
        if is_supabase_pooler_host(env.db_host):
            errors.append(
                "MAIN mode requires direct Supabase Postgres (db.<project-ref>.supabase.co:5432), "
                "not Session Pooler (*.pooler.supabase.com)."
            )
        elif not is_supabase_direct_host(env.db_host):
            errors.append(
                "MAIN DATABASE_URL must use direct Supabase host db.<project-ref>.supabase.co:5432."
            )

    if env.is_ephemeral:
        warnings.append(
            "Ephemeral DB detected (localhost/docker). Reports/costs may 'disappear' when volumes reset or environment changes."
        )

    if settings.debug:
        warnings.append("DEBUG=true in production is discouraged")
    if settings.maintenance_mode:
        warnings.append("MAINTENANCE_MODE=true — worker/dispatch/AI may be limited")
    if not settings.secret_key or settings.secret_key == "change-me":
        errors.append("SECRET_KEY must be set to a non-default value")
    if not settings.database_url:
        errors.append("DATABASE_URL is required")

    if settings.ai_enabled:
        provider = settings.ai_provider.lower().strip()
        has_key = bool(settings.ai_openai_api_key.strip())
        if provider == "mock" and has_key:
            warnings.append(
                "AI_OPENAI_API_KEY is set but AI_PROVIDER=mock — LLM calls will not use OpenAI"
            )
        elif provider not in ("mock", "") and not has_key:
            warnings.append(
                f"AI_PROVIDER={settings.ai_provider} but AI_OPENAI_API_KEY is empty — expect mock degradation"
            )
        if settings.ai_prompt_runtime_version != "v3":
            warnings.append(
                f"AI_PROMPT_RUNTIME_VERSION={settings.ai_prompt_runtime_version} (v3 recommended for seller testing)"
            )

    if settings.storage_backend.lower() == "supabase" and not settings.supabase_url.strip():
        if settings.allow_local_storage_fallback:
            warnings.append(
                "STORAGE_BACKEND=supabase without SUPABASE_URL — local upload fallback may be used"
            )
        else:
            warnings.append("STORAGE_BACKEND=supabase but SUPABASE_URL is empty — uploads will fail")

    if env.mode == "MAIN" and settings.storage_backend.lower() == "supabase" and settings.allow_local_storage_fallback:
        errors.append(
            "MAIN mode requires persistent Supabase Storage. Set ALLOW_LOCAL_STORAGE_FALLBACK=false."
        )

    ok = not errors
    if warnings:
        for w in warnings:
            logger.warning("startup_validation_warning", extra={"detail": w})
    if errors:
        for e in errors:
            logger.error("startup_validation_error", extra={"detail": e})
    return StartupValidationReport(ok=ok, warnings=tuple(warnings), errors=tuple(errors))


async def validate_database_consistency(db: AsyncSession) -> StartupValidationReport:
    warnings: list[str] = []
    errors: list[str] = []
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database connectivity failed: {exc}")
        return StartupValidationReport(False, tuple(warnings), tuple(errors))

    try:
        version = (
            await db.execute(text("SHOW server_version"))
        ).scalar_one_or_none()
        db_name = (await db.execute(text("SELECT current_database()"))).scalar_one_or_none()
        rls = (await db.execute(text("SHOW row_security"))).scalar_one_or_none()
        warnings.append(f"db={db_name} postgres={version} row_security={rls}")
    except Exception as exc:
        warnings.append(f"db metadata probe failed: {exc}")

    if settings.maintenance_mode:
        warnings.append("maintenance mode active at startup")

    return StartupValidationReport(ok=True, warnings=tuple(warnings), errors=tuple(errors))

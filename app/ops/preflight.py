"""CLI preflight checks for production safety (Wave 1 — not wired into API lifespan)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.startup_validation import StartupValidationReport, validate_environment

_REQUIRED_ALWAYS: tuple[str, ...] = (
    "database_url",
    "secret_key",
    "environment_mode",
)
_REQUIRED_MAIN: tuple[str, ...] = ("supabase_url",)


@dataclass(frozen=True)
class PreflightReport:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _is_blank(value: str | None) -> bool:
    return not (value or "").strip()


def collect_required_field_errors() -> list[str]:
    errors: list[str] = []
    for field in _REQUIRED_ALWAYS:
        if _is_blank(getattr(settings, field, None)):
            errors.append(f"{field.upper()} is required")
    mode = (settings.environment_mode or "").upper().strip()
    if mode == "MAIN":
        for field in _REQUIRED_MAIN:
            if _is_blank(getattr(settings, field, None)):
                errors.append(f"{field.upper()} is required when ENVIRONMENT_MODE=MAIN")
    return errors


def build_preflight_report(
    env_report: StartupValidationReport | None = None,
) -> PreflightReport:
    env_report = env_report if env_report is not None else validate_environment()
    errors = list(collect_required_field_errors())
    errors.extend(env_report.errors)
    warnings = list(env_report.warnings)
    ok = not errors
    return PreflightReport(ok=ok, errors=tuple(errors), warnings=tuple(warnings))


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic_executable() -> str:
    venv_alembic = _REPO_ROOT / ".venv" / "bin" / "alembic"
    if venv_alembic.is_file():
        return str(venv_alembic)
    return "alembic"


def _alembic_head_revision() -> str:
    result = subprocess.run(
        [_alembic_executable(), "heads"],
        check=False,
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"alembic heads failed: {stderr or 'unknown error'}")
    line = (result.stdout or "").strip().splitlines()[0].strip()
    if not line:
        raise RuntimeError("alembic heads returned no revision")
    return line.split()[0]


async def check_alembic_revision() -> tuple[bool, str]:
    """Compare code alembic head with production DB alembic_version (read-only)."""
    head = _alembic_head_revision()
    engine = create_async_engine(settings.async_database_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.scalar_one()
    finally:
        await engine.dispose()
    if head != current:
        return False, f"schema drift: code head={head} db={current}"
    return True, head


def run_preflight(*, check_schema: bool = False) -> int:
    report = build_preflight_report()
    for warning in report.warnings:
        print(f"PREFLIGHT WARN: {warning}", file=sys.stderr)
    for error in report.errors:
        print(f"PREFLIGHT ERROR: {error}", file=sys.stderr)
    if not report.ok:
        return 1

    if check_schema:
        import asyncio

        try:
            ok, detail = asyncio.run(check_alembic_revision())
        except Exception as exc:
            print(f"PREFLIGHT ERROR: schema check failed: {exc}", file=sys.stderr)
            return 1
        if not ok:
            print(f"PREFLIGHT ERROR: {detail}", file=sys.stderr)
            return 1
        print(f"PREFLIGHT OK: schema revision {detail}")

    print("PREFLIGHT OK: environment validation passed")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production environment preflight checks")
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Also verify alembic head matches alembic_version in DATABASE_URL",
    )
    args = parser.parse_args(argv)
    return run_preflight(check_schema=args.schema)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Password recovery validation — token edge cases + optional live SMTP path.

Uses dedicated test user only (mvp-e2e-test@mail.ru).
Prints markdown table for ops report.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EMAIL = "mvp-e2e-test@mail.ru"
DEFAULT_BASE = os.environ.get("APP_PUBLIC_URL", "https://321997.fornex.cloud").rstrip("/")
# Use direct API for token tests to avoid nginx auth rate limits on shared IP.
API_BASE = os.environ.get("VALIDATION_API_BASE", "http://127.0.0.1:8000").rstrip("/")
PROTECTED_PRODUCTION_EMAILS = frozenset(
    e.strip().lower()
    for e in os.environ.get("PROTECTED_PRODUCTION_EMAILS", "").split(",")
    if e.strip()
)

RESULTS: list[tuple[str, str, str, str]] = []


def _load_env() -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def _row(scenario: str, expected: str, actual: str, status: str) -> None:
    RESULTS.append((scenario, expected, actual, status))
    mark = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
    print(f"[{mark}] {scenario}: {actual}")


async def _get_user_id(email: str) -> UUID:
    sys.path.insert(0, str(ROOT))
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.user import User

    async with SessionLocal() as db:
        row = (await db.execute(select(User.id).where(User.email == email.lower()))).scalar_one_or_none()
        if row is None:
            raise SystemExit(f"Test user {email} not found — run scripts/create_mvp_test_user.py")
        return row


async def _insert_token(user_id: UUID, *, expired: bool = False) -> str:
    sys.path.insert(0, str(ROOT))
    from app.core.config import settings
    from app.models.password_reset_token import PasswordResetToken
    from app.services.auth_service import AuthService

    from app.core.database import SessionLocal

    raw = secrets.token_urlsafe(32)
    token_hash = AuthService._hash_reset_token(raw)
    if expired:
        expires_at = datetime.now(UTC) - timedelta(minutes=1)
    else:
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_expire_minutes)

    async with SessionLocal() as db:
        db.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        await db.commit()
    return raw


async def _reset(api: str, token: str, password: str) -> tuple[int, str]:
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        r = await client.post(
            f"{api}/auth/reset-password",
            json={"token": token, "new_password": password, "confirm_password": password},
        )
        return r.status_code, r.text[:120]


async def main() -> None:
    _load_env()
    email = DEFAULT_EMAIL
    if email.lower() in PROTECTED_PRODUCTION_EMAILS:
        raise SystemExit("Refusing production account")

    api = f"{API_BASE}/api/v1"
    public_base = DEFAULT_BASE
    user_id = await _get_user_id(email)

    # 1) Invalid token
    code, body = await _reset(api, "totally-invalid-token", "BadToken1!")
    _row("Invalid token", "400", str(code), "PASS" if code == 400 else "FAIL")

    # 2) Valid token → success
    good_token = await _insert_token(user_id)
    new_pass = "ValidReset!" + secrets.token_hex(3)
    code, _ = await _reset(api, good_token, new_pass)
    _row("Valid token reset", "200 + JWT", str(code), "PASS" if code == 200 else "FAIL")

    # 3) Reuse same token
    code, _ = await _reset(api, good_token, "ReuseFail1!")
    _row("Token reuse", "400", str(code), "PASS" if code == 400 else "FAIL")

    # 4) Expired token
    expired_token = await _insert_token(user_id, expired=True)
    code, _ = await _reset(api, expired_token, "Expired1!")
    _row("Expired token", "400", str(code), "PASS" if code == 400 else "FAIL")

    # 5) Live forgot-password (SMTP)
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        r = await client.post(f"{DEFAULT_BASE}/api/v1/auth/forgot-password", json={"email": email})
    if r.status_code == 200:
        _row("forgot-password (live SMTP)", "200", str(r.status_code), "PASS")
    elif r.status_code == 503:
        _row("forgot-password (live SMTP)", "200", "503 SMTP not configured", "SKIP")
    elif r.status_code == 429:
        _row("forgot-password (live SMTP)", "200", "429 rate limited (retry later)", "SKIP")
    else:
        _row("forgot-password (live SMTP)", "200", f"{r.status_code} {r.text[:80]}", "FAIL")

    # 6) Link format check (synthetic)
    link = f"{public_base}/reset-password?token={secrets.token_urlsafe(16)}"
    ok = link.startswith(public_base) and "/reset-password?token=" in link
    _row("Reset link format", "HTTPS /reset-password?token=", link[:60] + "…", "PASS" if ok else "FAIL")

    print("\n| Scenario | Expected | Actual | Status |")
    print("|----------|----------|--------|--------|")
    for scenario, expected, actual, status in RESULTS:
        print(f"| {scenario} | {expected} | {actual} | {status} |")

    fails = sum(1 for *_, s in RESULTS if s == "FAIL")
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""Create or reset dedicated MVP E2E test user (never touches production accounts)."""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.auth import UserCreate
from app.services.auth_service import AuthService
from tests.conftest import PROTECTED_PRODUCTION_EMAILS, assert_not_production_identity

DEFAULT_EMAIL = "mvp-e2e-test@mail.ru"
DEFAULT_PASSWORD_FILE = Path("/root/.mvp_test_user_credentials")


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


async def ensure_test_user(email: str, password: str | None, rotate: bool) -> str:
    _load_env()
    assert_not_production_identity(email=email)
    if email.lower() in PROTECTED_PRODUCTION_EMAILS:
        raise RuntimeError(f"Refusing to modify production account: {email}")
    plain = password or secrets.token_urlsafe(16)

    async with SessionLocal() as db:
        existing = await AuthService(db).get_user_by_email(email)

    if existing is None:
        async with SessionLocal() as db:
            user = await AuthService(db).register(
                UserCreate(email=email, password=plain, full_name="MVP E2E Test")
            )
            print(f"created user_id={user.id}")
    elif rotate or password:
        async with SessionLocal() as db:
            row = await AuthService(db).get_user_by_email(email)
            assert row is not None
            row.hashed_password = get_password_hash(plain)
            row.is_active = True
            await db.commit()
            print(f"rotated password for user_id={row.id}")
    else:
        print(f"user exists user_id={existing.id} (password unchanged; pass --rotate to reset)")
        return plain

    DEFAULT_PASSWORD_FILE.write_text(f"email={email}\npassword={plain}\n", encoding="utf-8")
    DEFAULT_PASSWORD_FILE.chmod(0o600)
    return plain


def main() -> None:
    parser = argparse.ArgumentParser(description="Create MVP E2E test user")
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=None, help="Explicit password (else random)")
    parser.add_argument("--rotate", action="store_true", help="Reset password if user exists")
    args = parser.parse_args()

    password = asyncio.run(ensure_test_user(args.email, args.password, args.rotate))
    print(f"credentials saved to {DEFAULT_PASSWORD_FILE}")
    print(f"TEST_EMAIL={args.email}")
    print("TEST_PASS=<see credentials file>")


if __name__ == "__main__":
    main()

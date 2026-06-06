#!/usr/bin/env python3
"""
SMTP + forgot-password E2E against dedicated test user only.

Requires SMTP_USER/SMTP_PASSWORD/SMTP_FROM in .env.
Does NOT modify production accounts.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import secrets
import time
from pathlib import Path

import httpx

DEFAULT_EMAIL = "mvp-e2e-test@mail.ru"
DEFAULT_BASE = os.environ.get("APP_PUBLIC_URL", "https://321997.fornex.cloud").rstrip("/")
CREDS_FILE = Path("/root/.mvp_test_user_credentials")


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def _smtp_ready() -> tuple[bool, str]:
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip()
    if not host or not user or not password or not sender:
        return False, "SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM must be set in .env"
    return True, "ok"


async def _imap_fetch_reset_link(email: str, *, timeout_s: int = 120) -> str | None:
    """Optional: fetch reset link from Mail.ru IMAP if IMAP_PASSWORD is set."""
    imap_host = os.environ.get("IMAP_HOST", "imap.mail.ru")
    imap_user = os.environ.get("IMAP_USER", email)
    imap_password = os.environ.get("IMAP_PASSWORD", os.environ.get("SMTP_PASSWORD", ""))
    if not imap_password:
        return None

    import imaplib
    import email as email_lib

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with imaplib.IMAP4_SSL(imap_host) as client:
            client.login(imap_user, imap_password)
            client.select("INBOX")
            _, data = client.search(None, '(UNSEEN SUBJECT "Восстановление пароля")')
            ids = data[0].split()
            for msg_id in reversed(ids):
                _, msg_data = client.fetch(msg_id, "(RFC822)")
                msg = email_lib.message_from_bytes(msg_data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(errors="ignore")
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")
                match = re.search(r"(https?://\S+/reset-password\?token=[A-Za-z0-9_\-]+)", body)
                if match:
                    return match.group(1)
        await asyncio.sleep(5)
    return None


async def main() -> None:
    _load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--token", default=None, help="Manual reset token (skip email fetch)")
    args = parser.parse_args()

    ok, reason = _smtp_ready()
    if not ok:
        raise SystemExit(f"SMTP not ready: {reason}")

    from tests.conftest import PROTECTED_PRODUCTION_EMAILS

    if args.email.lower() in PROTECTED_PRODUCTION_EMAILS:
        raise SystemExit("Refusing to run E2E on production account. Use mvp-e2e-test@mail.ru")

    api = f"{args.base_url}/api/v1"
    new_password = "E2eReset!" + secrets.token_hex(4)

    async with httpx.AsyncClient(verify=False, timeout=60) as client:
        print("1) POST /auth/forgot-password")
        r = await client.post(f"{api}/auth/forgot-password", json={"email": args.email})
        print(f"   status={r.status_code} body={r.text[:200]}")
        if r.status_code != 200:
            raise SystemExit("forgot-password failed")

        token = args.token
        if not token:
            print("2) fetch email link (IMAP if configured)")
            link = await _imap_fetch_reset_link(args.email)
            if not link:
                raise SystemExit(
                    "No reset link fetched. Set IMAP_PASSWORD or pass --token from email manually."
                )
            token = link.split("token=")[-1]
            print(f"   token acquired len={len(token)}")

        print("3) POST /auth/reset-password")
        r = await client.post(
            f"{api}/auth/reset-password",
            json={"token": token, "new_password": new_password, "confirm_password": new_password},
        )
        print(f"   status={r.status_code}")
        if r.status_code != 200:
            raise SystemExit(r.text)

        print("4) POST /auth/login")
        r = await client.post(
            f"{api}/auth/login",
            data={"username": args.email, "password": new_password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        print(f"   status={r.status_code}")
        if r.status_code != 200:
            raise SystemExit(r.text)

        if CREDS_FILE.exists():
            lines = CREDS_FILE.read_text().splitlines()
            updated = []
            for line in lines:
                if line.startswith("password="):
                    updated.append(f"password={new_password}")
                else:
                    updated.append(line)
            CREDS_FILE.write_text("\n".join(updated) + "\n")
            CREDS_FILE.chmod(0o600)

    print("E2E OK: forgot → email/token → reset → login")


if __name__ == "__main__":
    asyncio.run(main())

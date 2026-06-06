#!/usr/bin/env python3
"""Verify SMTP configuration; optionally send a test email."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def _status() -> tuple[bool, list[str]]:
    issues: list[str] = []
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip()
    if not host:
        issues.append("SMTP_HOST missing")
    if not sender:
        issues.append("SMTP_FROM missing")
    if not user:
        issues.append("SMTP_USER missing (Mail.ru requires auth)")
    if not password:
        issues.append("SMTP_PASSWORD missing (use Mail.ru app password)")
    return not issues, issues


async def _send_test(to: str) -> None:
    sys.path.insert(0, str(ROOT))
    from app.services.email_service import send_email

    await send_email(
        to=to,
        subject="Marketplace Analytics — SMTP test",
        body="SMTP verification message. If you received this, forgot-password email delivery is ready.",
    )


def main() -> int:
    _load_env()
    parser = argparse.ArgumentParser(description="SMTP configuration verify")
    parser.add_argument("--check-only", action="store_true", help="Validate env only")
    parser.add_argument("--to", default=os.environ.get("SMTP_USER", ""), help="Test recipient")
    args = parser.parse_args()

    ok, issues = _status()
    if ok:
        print("OK  SMTP configuration complete")
        print(f"    host={os.environ.get('SMTP_HOST')} from={os.environ.get('SMTP_FROM')}")
    else:
        print("FAIL SMTP configuration incomplete:")
        for i in issues:
            print(f"  - {i}")
        print("\nSee docs/operations/smtp_setup_checklist.md")
        return 1

    if args.check_only:
        return 0

    if not args.to:
        print("FAIL --to required for send test")
        return 1

    asyncio.run(_send_test(args.to))
    print(f"OK  test email sent to {args.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Configure Uptime Kuma monitors and notifications for MVP pilot."""

from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDS_FILE = Path("/root/.uptime_kuma_credentials")
KUMA_URL = os.environ.get("UPTIME_KUMA_URL", "http://127.0.0.1:3001")
PUBLIC_BASE = os.environ.get("APP_PUBLIC_URL", "https://321997.fornex.cloud").rstrip("/")


def _load_env() -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def _creds() -> tuple[str, str]:
    if CREDS_FILE.exists():
        data = {}
        for line in CREDS_FILE.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()
        if data.get("username") and data.get("password"):
            return data["username"], data["password"]
    user = os.environ.get("UPTIME_KUMA_USER", "marketplace_ops")
    password = os.environ.get("UPTIME_KUMA_PASSWORD") or secrets.token_urlsafe(16)
    CREDS_FILE.write_text(f"username={user}\npassword={password}\n", encoding="utf-8")
    CREDS_FILE.chmod(0o600)
    return user, password


def main() -> int:
    _load_env()
    from uptime_kuma_api import MonitorType, NotificationType, UptimeKumaApi

    user, password = _creds()
    monitors_spec = [
        {
            "name": "Frontend",
            "type": MonitorType.HTTP,
            "url": f"{PUBLIC_BASE}/",
            "interval": 120,
            "maxretries": 2,
        },
        {
            "name": "API /health",
            "type": MonitorType.KEYWORD,
            "url": f"{PUBLIC_BASE}/health",
            "keyword": '"status":"ok"',
            "interval": 60,
            "maxretries": 2,
        },
        {
            "name": "API /health/ready",
            "type": MonitorType.KEYWORD,
            "url": f"{PUBLIC_BASE}/health/ready",
            "keyword": '"status":"ready"',
            "interval": 60,
            "maxretries": 2,
        },
    ]

    with UptimeKumaApi(KUMA_URL, timeout=30) as api:
        try:
            api.login(user, password)
        except Exception:
            api.setup(user, password)
            api.login(user, password)

        notif_id = None
        notif_name = "Pilot Email (SMTP)"
        tg_token = os.environ.get("UPTIME_KUMA_TELEGRAM_BOT_TOKEN", "").strip()
        tg_chat = os.environ.get("UPTIME_KUMA_TELEGRAM_CHAT_ID", "").strip()
        notif_type = None
        notif_kwargs: dict = {"isDefault": True}

        if tg_token and tg_chat:
            notif_name = "Pilot Telegram"
            notif_type = NotificationType.TELEGRAM
            notif_kwargs.update(telegramBotToken=tg_token, telegramChatID=tg_chat)
        elif (
            os.environ.get("SMTP_HOST")
            and os.environ.get("SMTP_FROM")
            and os.environ.get("SMTP_USER")
            and os.environ.get("SMTP_PASSWORD")
        ):
            notif_type = NotificationType.SMTP
            notif_kwargs.update(
                smtpHost=os.environ["SMTP_HOST"],
                smtpPort=int(os.environ.get("SMTP_PORT", "587")),
                smtpSecure=os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes"),
                smtpUsername=os.environ["SMTP_USER"],
                smtpPassword=os.environ["SMTP_PASSWORD"],
                smtpFrom=os.environ["SMTP_FROM"],
                smtpTo=os.environ["SMTP_FROM"],
            )
        else:
            print("WARN no Telegram/SMTP credentials — monitors without notifications")

        if notif_type:
            result = api.add_notification(name=notif_name, type=notif_type, **notif_kwargs)
            notif_id = result.get("id")
            print(f"notification added: {notif_name} id={notif_id}")
            try:
                test = api.test_notification(type=notif_type, name=notif_name, **notif_kwargs)
                print(f"test_notification: {test}")
            except Exception as exc:
                print(f"test_notification: {exc}")

        existing = {m.get("name"): m for m in api.get_monitors()}
        monitor_ids: list[int] = []
        for spec in monitors_spec:
            name = spec["name"]
            if name in existing:
                monitor_ids.append(existing[name]["id"])
                print(f"monitor exists: {name} id={existing[name]['id']}")
                continue
            if notif_id:
                spec = {**spec, "notificationIDList": [notif_id]}
            result = api.add_monitor(**spec)
            mid = result.get("monitorID") or result.get("monitorId")
            monitor_ids.append(mid)
            print(f"monitor added: {name} id={mid}")

        print("\n--- Monitors ---")
        for m in api.get_monitors():
            if m.get("type") != "group":
                print(json.dumps({
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "type": m.get("type"),
                    "url": m.get("url"),
                    "active": m.get("active"),
                }, ensure_ascii=False))

    print(f"\nUptime Kuma UI: {KUMA_URL} user={user} password stored in {CREDS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

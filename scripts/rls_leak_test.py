#!/usr/bin/env python3
"""SQL + API tenant isolation proof (user_a data invisible to user_b)."""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.core.tenant_context import set_bypass_rls_context, set_current_user_context, set_queue_role_context
from app.models.user import User


def _load_env() -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


async def _counts(db, uid: UUID, table: str) -> dict[str, int]:
    owned = (
        await db.execute(
            text(f"SELECT count(*) FROM {table} WHERE user_id = :u"),
            {"u": str(uid)},
        )
    ).scalar()
    visible = (await db.execute(text(f"SELECT count(*) FROM {table}"))).scalar()
    return {"owned_rows": int(owned), "visible_rows": int(visible)}


async def main() -> int:
    _load_env()
    suffix = secrets.token_hex(4)
    email_a = f"rls-proof-a-{suffix}@mail.ru"
    email_b = f"rls-proof-b-{suffix}@mail.ru"
    pw = "RlsProof!" + secrets.token_hex(4)

    async with SessionLocal() as db:
        async with db.begin():
            role = (await db.execute(text("SELECT current_user"))).scalar()
            ua = User(email=email_a, hashed_password=get_password_hash(pw), full_name="RLS A", is_active=True)
            ub = User(email=email_b, hashed_password=get_password_hash(pw), full_name="RLS B", is_active=True)
            db.add(ua)
            db.add(ub)
            await db.flush()
            id_a, id_b = ua.id, ub.id
        await db.commit()

    report_path = ROOT / "tests/Еженедельный детализированный отчет WB.xlsx"
    with httpx.Client(timeout=120) as client:
        token_a = client.post(
            "http://127.0.0.1:8000/api/v1/auth/login",
            data={"username": email_a, "password": pw},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).json()["access_token"]
        with report_path.open("rb") as f:
            up = client.post(
                "http://127.0.0.1:8000/api/v1/reports/upload",
                headers={"Authorization": f"Bearer {token_a}"},
                files={"file": (report_path.name, f)},
                data={"marketplace": "wildberries", "report_type": "sales"},
            )
        token_b = client.post(
            "http://127.0.0.1:8000/api/v1/auth/login",
            data={"username": email_b, "password": pw},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).json()["access_token"]
        hb = {"Authorization": f"Bearer {token_b}"}
        api_reports = client.get("http://127.0.0.1:8000/api/v1/reports", headers=hb)
        api_costs = client.get("http://127.0.0.1:8000/api/v1/costs", headers=hb)
        dash = client.get(
            "http://127.0.0.1:8000/api/v1/dashboard/summary",
            headers=hb,
            params={"marketplace": "wildberries", "start": "2025-01-01", "end": "2026-12-31"},
        )
        rev = dash.json().get("revenue_summary", {}).get("kpis", {}).get("total_revenue") if dash.status_code == 200 else None

    print(f"db_role_at_runtime={role}")
    print(f"user_a={email_a} id={id_a}")
    print(f"user_b={email_b} id={id_b}")
    print(f"upload_user_a HTTP {up.status_code}")
    print(
        f"API user_b: reports={len(api_reports.json()) if api_reports.status_code==200 else api_reports.status_code} "
        f"costs={len(api_costs.json()) if api_costs.status_code==200 else api_costs.status_code} "
        f"dashboard_revenue={rev}"
    )

    tables = ["reports", "cost_history", "financial_ledger_entries", "daily_aggregates", "sku_daily_metrics"]
    print("\n=== SQL user_b (ctx set, bypass=false) ===")
    ok = True
    async with SessionLocal() as db:
        async with db.begin():
            await set_bypass_rls_context(db, False)
            await set_queue_role_context(db, False)
            await set_current_user_context(db, id_b)
            for t in tables:
                row = await _counts(db, id_b, t)
                force = (
                    await db.execute(
                        text(
                            """
                            SELECT c.relforcerowsecurity FROM pg_class c
                            JOIN pg_namespace n ON n.oid=c.relnamespace
                            WHERE n.nspname='public' AND c.relname=:t
                            """
                        ),
                        {"t": t},
                    )
                ).scalar()
                print(f"{t}: owned={row['owned_rows']} visible={row['visible_rows']} force_rls={force}")
                if row["owned_rows"] != row["visible_rows"]:
                    ok = False

    print("\nRESULT:", "NO CROSS TENANT LEAK" if ok and api_costs.status_code == 200 and len(api_costs.json()) == row["owned_rows"] else "LEAK DETECTED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""
UX-2: Real data validation harness (product-facing).

This script intentionally does NOT change backend semantics. It exercises existing APIs:

- register/login
- report upload
- report status polling
- costs import
- optional AI intelligence run
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


def login(base_url: str, api_prefix: str, email: str, password: str) -> str:
    url = f"{base_url}{api_prefix}/auth/login"
    r = requests.post(url, data={"username": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def register(base_url: str, api_prefix: str, email: str, password: str) -> None:
    url = f"{base_url}{api_prefix}/auth/register"
    r = requests.post(url, json={"email": email, "password": password}, timeout=30)
    if r.status_code in (200, 201):
        return
    # Allow re-run
    if r.status_code == 409:
        return
    r.raise_for_status()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def upload_report(
    base_url: str,
    api_prefix: str,
    token: str,
    marketplace: str,
    report_type: str,
    file_path: Path,
) -> dict:
    url = f"{base_url}{api_prefix}/reports/upload"
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f)}
        data = {"marketplace": marketplace, "report_type": report_type}
        r = requests.post(url, headers=auth_headers(token), files=files, data=data, timeout=120)
        r.raise_for_status()
        return r.json()


def get_report(base_url: str, api_prefix: str, token: str, report_id: str) -> dict:
    url = f"{base_url}{api_prefix}/reports/{report_id}"
    r = requests.get(url, headers=auth_headers(token), timeout=30)
    r.raise_for_status()
    return r.json()


def import_costs(base_url: str, api_prefix: str, token: str, file_path: Path) -> list[dict]:
    url = f"{base_url}{api_prefix}/costs/import"
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f)}
        r = requests.post(url, headers=auth_headers(token), files=files, timeout=60)
        r.raise_for_status()
        return r.json()


def run_intelligence(base_url: str, api_prefix: str, token: str, report_id: str | None) -> dict:
    url = f"{base_url}{api_prefix}/ai/intelligence/runs"
    body = {
        "workflow": "inventory_insight",
        "prompt_id": "inventory.insight.v1",
        "semantics_version": "1.0",
        "report_id": report_id,
    }
    r = requests.post(url, headers=auth_headers(token), json=body, timeout=120)
    r.raise_for_status()
    return r.json()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--api-prefix", default="/api/v1")
    ap.add_argument("--email", default="demo_seller@example.com")
    ap.add_argument("--password", default="demo_password_123")
    ap.add_argument("--marketplace", default="wildberries")
    ap.add_argument("--report-type", default="sales")
    ap.add_argument("--report-file", required=True)
    ap.add_argument("--costs-file", required=False)
    ap.add_argument("--poll-seconds", type=int, default=3)
    ap.add_argument("--poll-timeout-seconds", type=int, default=180)
    ap.add_argument("--run-ai", action="store_true")
    args = ap.parse_args()

    report_file = Path(args.report_file)
    if not report_file.exists():
        raise SystemExit(f"report file not found: {report_file}")

    if args.costs_file:
        costs_file = Path(args.costs_file)
        if not costs_file.exists():
            raise SystemExit(f"costs file not found: {costs_file}")
    else:
        costs_file = None

    register(args.base_url, args.api_prefix, args.email, args.password)
    token = login(args.base_url, args.api_prefix, args.email, args.password)

    t0 = time.time()
    uploaded = upload_report(
        args.base_url, args.api_prefix, token, args.marketplace, args.report_type, report_file
    )
    report_id = uploaded["report"]["id"]
    t1 = time.time()

    print(json.dumps({"event": "upload_complete", "elapsed_s": round(t1 - t0, 3), "report_id": report_id}, ensure_ascii=False))

    if costs_file:
        t2 = time.time()
        rows = import_costs(args.base_url, args.api_prefix, token, costs_file)
        t3 = time.time()
        print(
            json.dumps(
                {"event": "cost_import_complete", "elapsed_s": round(t3 - t2, 3), "rows": len(rows)},
                ensure_ascii=False,
            )
        )

    # Poll report processing lifecycle
    deadline = time.time() + args.poll_timeout_seconds
    status = "unknown"
    while time.time() < deadline:
        rep = get_report(args.base_url, args.api_prefix, token, report_id)
        status = str(rep.get("status", "unknown")).lower()
        print(json.dumps({"event": "poll", "status": status, "job": rep.get("job")}, ensure_ascii=False))
        if status in ("processed", "failed"):
            break
        time.sleep(args.poll_seconds)

    print(json.dumps({"event": "final", "status": status, "report_id": report_id}, ensure_ascii=False))

    if args.run_ai:
        t4 = time.time()
        res = run_intelligence(args.base_url, args.api_prefix, token, report_id)
        t5 = time.time()
        print(
            json.dumps(
                {
                    "event": "ai_intelligence_complete",
                    "elapsed_s": round(t5 - t4, 3),
                    "recommendation_id": res.get("recommendation_id"),
                    "summary": res.get("summary"),
                    "confidence": res.get("confidence"),
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()


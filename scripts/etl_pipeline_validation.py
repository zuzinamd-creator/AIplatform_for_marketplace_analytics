#!/usr/bin/env python3
"""
ETL pipeline validation — upload → job → worker → aggregates → UI data.

Uses dedicated MVP test user and real WB XLSX fixture.
Prints per-stage timings and PASS/FAIL verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "tests/Еженедельный детализированный отчет WB.xlsx"
DEFAULT_COSTS = ROOT / "docs/product/fixtures/sample_costs.csv"
CREDS_FILE = Path("/root/.mvp_test_user_credentials")
DEFAULT_EMAIL = "mvp-e2e-test@mail.ru"
DEFAULT_BASE = os.environ.get("APP_PUBLIC_URL", "https://321997.fornex.cloud").rstrip("/")

STAGES: list[dict] = []


def _load_env() -> None:
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def _stage(name: str, t0: float, *, ok: bool, detail: str = "") -> None:
    elapsed = time.time() - t0
    STAGES.append({"stage": name, "elapsed_s": round(elapsed, 2), "ok": ok, "detail": detail})
    mark = "OK" if ok else "FAIL"
    print(f"[{mark}] {name}: {elapsed:.2f}s {detail}")


def _login(base: str, prefix: str, email: str, password: str) -> str:
    r = requests.post(
        f"{base}{prefix}/auth/login",
        data={"username": email, "password": password},
        timeout=30,
        verify=False,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    _load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--api-prefix", default="/api/v1")
    ap.add_argument("--email", default=DEFAULT_EMAIL)
    ap.add_argument("--report-file", default=str(DEFAULT_REPORT))
    ap.add_argument("--costs-file", default=str(DEFAULT_COSTS))
    ap.add_argument("--poll-seconds", type=int, default=3)
    ap.add_argument("--poll-timeout", type=int, default=300)
    args = ap.parse_args()

    password = os.environ.get("TEST_PASS", "")
    if not password and CREDS_FILE.exists():
        for line in CREDS_FILE.read_text().splitlines():
            if line.startswith("password="):
                password = line.split("=", 1)[1]

    report_path = Path(args.report_file)
    if not report_path.exists():
        print(f"FAIL report fixture missing: {report_path}")
        return 1
    if not password:
        print("FAIL TEST_PASS / credentials file required")
        return 1

    base = args.base_url.rstrip("/")
    prefix = args.api_prefix
    ok_all = True

    t0 = time.time()
    try:
        token = _login(base, prefix, args.email, password)
        _stage("1_login", t0, ok=True)
    except Exception as exc:
        _stage("1_login", t0, ok=False, detail=str(exc))
        return 1

    # Upload report
    t0 = time.time()
    try:
        with report_path.open("rb") as f:
            r = requests.post(
                f"{base}{prefix}/reports/upload",
                headers=_headers(token),
                files={"file": (report_path.name, f)},
                data={"marketplace": "wildberries", "report_type": "sales"},
                timeout=180,
                verify=False,
            )
        r.raise_for_status()
        payload = r.json()
        report_id = payload["report"]["id"]
        job_id = (payload.get("job") or {}).get("id") or payload.get("job_id", "n/a")
        _stage("2_upload_report", t0, ok=True, detail=f"report_id={report_id} job={job_id}")
    except Exception as exc:
        _stage("2_upload_report", t0, ok=False, detail=str(exc))
        ok_all = False
        report_id = None

    # Poll ETL job / report status
    t0 = time.time()
    final_status = "unknown"
    job_status = "unknown"
    if report_id:
        deadline = time.time() + args.poll_timeout
        while time.time() < deadline:
            r = requests.get(
                f"{base}{prefix}/reports/{report_id}",
                headers=_headers(token),
                timeout=30,
                verify=False,
            )
            r.raise_for_status()
            rep = r.json()
            final_status = str(rep.get("status", "unknown")).lower()
            job = rep.get("job") or {}
            job_status = str(job.get("status", "unknown")).lower()
            if final_status in ("processed", "failed") or job_status in ("completed", "dead_letter", "failed"):
                break
            time.sleep(args.poll_seconds)
        ok = final_status == "processed" and job_status in ("completed", "unknown", "")
        if job_status == "completed":
            ok = final_status == "processed"
        _stage(
            "3_worker_etl_job",
            t0,
            ok=ok,
            detail=f"report={final_status} job={job_status}",
        )
        if not ok:
            ok_all = False
    else:
        _stage("3_worker_etl_job", t0, ok=False, detail="skipped")
        ok_all = False

    # Dashboard aggregates visible
    t0 = time.time()
    try:
        r = requests.get(
            f"{base}{prefix}/dashboard/summary",
            headers=_headers(token),
            params={"marketplace": "wildberries", "start": "2025-01-01", "end": "2026-12-31"},
            timeout=60,
            verify=False,
        )
        r.raise_for_status()
        summary = r.json()
        has_kpi = bool(summary.get("kpis") or summary.get("revenue") is not None or summary)
        _stage("4_dashboard_aggregates", t0, ok=r.status_code == 200 and has_kpi, detail=f"keys={list(summary.keys())[:6]}")
    except Exception as exc:
        _stage("4_dashboard_aggregates", t0, ok=False, detail=str(exc))
        ok_all = False

    # Costs list (import optional smoke)
    t0 = time.time()
    try:
        costs_path = Path(args.costs_file)
        if costs_path.exists():
            with costs_path.open("rb") as f:
                r = requests.post(
                    f"{base}{prefix}/costs/import",
                    headers=_headers(token),
                    files={"file": (costs_path.name, f)},
                    timeout=60,
                    verify=False,
                )
            import_ok = r.status_code in (200, 201)
        else:
            r = requests.get(f"{base}{prefix}/costs", headers=_headers(token), timeout=30, verify=False)
            import_ok = r.status_code == 200
        _stage("5_costs_endpoint", t0, ok=import_ok, detail=f"http={r.status_code}")
    except Exception as exc:
        _stage("5_costs_endpoint", t0, ok=False, detail=str(exc))
        ok_all = False

    # Worker log errors (last 5 min)
    t0 = time.time()
    import subprocess

    proc = subprocess.run(
        ["journalctl", "-u", "marketplace-worker", "--since", "10 min ago", "--no-pager", "-p", "err"],
        capture_output=True,
        text=True,
    )
    err_lines = [ln for ln in proc.stdout.splitlines() if ln.strip() and "error" in ln.lower()]
    _stage("6_worker_logs_clean", t0, ok=len(err_lines) == 0, detail=f"errors={len(err_lines)}")

    print("\n| Stage | Time (s) | Status | Detail |")
    print("|-------|----------|--------|--------|")
    for s in STAGES:
        st = "PASS" if s["ok"] else "FAIL"
        print(f"| {s['stage']} | {s['elapsed_s']} | {st} | {s['detail'][:60]} |")

    print("\nRESULT:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

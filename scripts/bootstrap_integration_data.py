from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass(frozen=True)
class Env:
    base_url: str
    email: str
    password: str


def _env() -> Env:
    return Env(
        base_url=os.getenv("INTEGRATION_BASE_URL", "http://localhost:8081").rstrip("/"),
        email=os.getenv("INTEGRATION_EMAIL", "integration@example.com"),
        password=os.getenv("INTEGRATION_PASSWORD", "integration-password-123"),
    )


def _find_test_xlsx() -> Path:
    tests_dir = Path(__file__).resolve().parents[1] / "tests"
    matches = sorted(tests_dir.glob("*.xlsx"))
    if not matches:
        raise SystemExit(f"No .xlsx files in {tests_dir}. Add a deterministic WB weekly test report (*.xlsx).")
    return matches[0]


def _now_date_iso() -> str:
    # keep it simple: rely on server-side defaults / selected periods in UI.
    # For deterministic API checks, we query /coverage first and use its available range.
    return ""


def _wait_ok(client: httpx.Client, url: str, timeout_s: int = 60) -> None:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            r = client.get(url, timeout=5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit(f"Service not ready: {url}")


def _poll_coverage_range(client: httpx.Client, *, timeout_s: int = 240) -> tuple[str, str]:
    start = time.time()
    last = None
    while time.time() - start < timeout_s:
        r = client.get("/api/v1/analytics/coverage")
        if r.status_code == 200:
            cov = r.json()
            a = cov.get("available_min_date")
            b = cov.get("available_max_date")
            if a and b:
                return a, b
            last = cov
        time.sleep(2)
    raise SystemExit(
        "No aggregates available yet (coverage has no available_min_date/max_date). "
        "Ensure worker is running and report processing finished."
        + (f" last_coverage={last}" if last is not None else "")
    )


def main() -> None:
    env = _env()
    with httpx.Client(base_url=env.base_url, timeout=300) as client:
        _wait_ok(client, "/health", timeout_s=90)

        # Register (idempotent-ish for local run)
        r = client.post("/api/v1/auth/register", json={"email": env.email, "password": env.password})
        if r.status_code in (200, 201, 409):
            pass
        elif r.status_code == 400 and "already" in r.text.lower():
            pass
        else:
            raise SystemExit(f"register failed: {r.status_code} {r.text}")

        # Login
        r = client.post(
            "/api/v1/auth/login",
            data={"username": env.email, "password": env.password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code != 200:
            raise SystemExit(f"login failed: {r.status_code} {r.text}")
        token = r.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"

        # Upload report
        xlsx = _find_test_xlsx()
        files = {"file": (xlsx.name, xlsx.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        data = {"marketplace": "wildberries", "report_type": "sales"}
        r = client.post("/api/v1/reports/upload", data=data, files=files)
        if r.status_code not in (200, 201):
            raise SystemExit(f"upload failed: {r.status_code} {r.text}")

        # Coverage → wait for worker to build aggregates
        start, end = _poll_coverage_range(client, timeout_s=300)

        params = {"marketplace": "wildberries", "start": start, "end": end}

        # KPI endpoints (dashboard surface)
        for path in (
            "/api/v1/analytics/kpis/summary",
            "/api/v1/analytics/kpis/trends/daily",
            "/api/v1/analytics/kpis/finance/summary",
            "/api/v1/analytics/kpis/finance/trends/daily",
            "/api/v1/analytics/sku-economics",
            "/api/v1/analytics/reconciliation/period",
            "/api/v1/analytics/cost-coverage",
        ):
            rr = client.get(path, params=params)
            if rr.status_code != 200:
                raise SystemExit(f"{path} failed: {rr.status_code} {rr.text}")

        # AI period intelligence (mock)
        body = {
            "workflow": "revenue_insight",
            "prompt_id": "analytics.summary.v1",
            "semantics_version": "1.0",
            "marketplace": "wildberries",
            "period_start": start,
            "period_end": end,
        }
        rr = client.post("/api/v1/ai/intelligence/period-runs", json=body)
        if rr.status_code not in (200, 201):
            raise SystemExit(f"ai period run failed: {rr.status_code} {rr.text}")

        print("OK: bootstrap integration data + endpoints passed")


if __name__ == "__main__":
    main()


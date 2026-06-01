#!/usr/bin/env python3
"""Local runtime smoke test — health, DB readiness, auth, ops/AI status.

Usage (from repo root, venv activated):
  python scripts/local/run-local-smoke-test.py
  set SMOKE_BASE_URL=http://localhost:8080
  set SMOKE_SKIP_AI_PROBE=1
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = os.environ.get("SMOKE_BASE_URL", "http://localhost:8080").rstrip("/")
API = f"{BASE}/api/v1"
TIMEOUT = float(os.environ.get("SMOKE_TIMEOUT_SECONDS", "30"))
SKIP_AI_PROBE = os.environ.get("SMOKE_SKIP_AI_PROBE", "").lower() in ("1", "true", "yes")


def _get(path: str, headers: dict | None = None) -> tuple[int, dict | str]:
    req = Request(f"{BASE}{path}", headers=headers or {})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except URLError as exc:
        raise RuntimeError(f"GET {path} failed: {exc}") from exc


def _post(path: str, payload: dict, headers: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json", **(headers or {})}
    req = Request(f"{API}{path}", data=data, headers=h, method="POST")
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, body
    except URLError as exc:
        raise RuntimeError(f"POST {path} failed: {exc}") from exc


def _ok(name: str) -> None:
    print(f"  OK  {name}")


def _fail(name: str, detail: str) -> None:
    print(f"  FAIL {name}: {detail}")


def main() -> int:
    errors: list[str] = []
    print(f"Smoke test base URL: {BASE}\n")

    print("1. Liveness / readiness")
    try:
        code, body = _get("/health")
        if code == 200 and isinstance(body, dict) and body.get("status") == "ok":
            _ok("/health")
        else:
            errors.append("/health")
            _fail("/health", str(body))
    except RuntimeError as exc:
        errors.append("/health")
        _fail("/health", str(exc))

    try:
        code, body = _get("/health/ready")
        if code == 200 and isinstance(body, dict) and body.get("status") == "ready":
            _ok("/health/ready (PostgreSQL)")
        else:
            errors.append("/health/ready")
            _fail("/health/ready", str(body))
    except RuntimeError as exc:
        errors.append("/health/ready")
        _fail("/health/ready", str(exc))

    print("\n2. Auth + protected health")
    email = f"smoke_{uuid.uuid4().hex[:12]}@local.test"
    password = "SmokeTest123!"
    code, reg = _post(
        "/auth/register",
        {"email": email, "password": password, "full_name": "Smoke Tester"},
    )
    if code not in (200, 201):
        errors.append("register")
        _fail("register", f"{code} {reg}")
        token = None
    else:
        _ok("register")
        code, login = _post("/auth/login", {"email": email, "password": password})
        if code != 200 or not isinstance(login, dict) or "access_token" not in login:
            errors.append("login")
            _fail("login", f"{code} {login}")
            token = None
        else:
            _ok("login")
            token = login["access_token"]

    if token:
        auth = {"Authorization": f"Bearer {token}"}
        code, ops = _get("/api/v1/ops/runtime/health", headers=auth)
        if code == 200:
            _ok("/api/v1/ops/runtime/health")
        else:
            errors.append("ops/runtime/health")
            _fail("ops/runtime/health", f"{code} {ops}")

        code, prov = _get("/api/v1/ai/providers/status", headers=auth)
        if code == 200 and isinstance(prov, dict):
            _ok("/api/v1/ai/providers/status")
            primary = prov.get("primary_provider", "")
            print(f"      primary_provider={primary!r} prompt_v3={prov.get('prompt_runtime_version')!r}")
            if primary == "mock":
                print("      WARN: AI_PROVIDER is mock — set openai/openrouter in .env for real LLM testing")
            unhealthy = [
                p.get("provider_id")
                for p in (prov.get("providers") or [])
                if isinstance(p, dict) and p.get("healthy") is False
            ]
            if unhealthy:
                print(f"      WARN: unhealthy providers in snapshot: {unhealthy}")
        else:
            errors.append("ai/providers/status")
            _fail("ai/providers/status", f"{code} {prov}")

        if not SKIP_AI_PROBE:
            print("\n3. Optional LLM connectivity (settings from server .env)")
            try:
                from app.ai.providers.failover import resolve_llm_provider

                res = resolve_llm_provider(model="gpt-4o-mini")
                if res.degraded_to_mock:
                    print("      SKIP live LLM probe (degraded to mock)")
                else:
                    import asyncio

                    from app.ai.providers.types import LLMMessage, LLMRequest

                    async def _ping() -> str:
                        out = await res.adapter.complete(
                            LLMRequest(
                                model=res.model,
                                messages=(LLMMessage(role="user", content="Reply with exactly: pong"),),
                                max_tokens=16,
                            )
                        )
                        return (out.content or "").strip()[:80]

                    text = asyncio.run(_ping())
                    _ok(f"LLM probe via {res.provider_id}: {text!r}")
            except Exception as exc:
                print(f"      WARN LLM probe: {exc}")

    print("\n---")
    if errors:
        print(f"FAILED ({len(errors)}): {', '.join(errors)}")
        print("See docs/testing/local_runtime_testing.md")
        return 1
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# Production Safety (Phase 8.2.0)

**Status:** Wave 2 implementation complete in repository (systemd units + docs; **not yet deployed to VPS**)  
**Wave 1 baseline:** `2e9aaad` — tooling committed  
**Phase 8.1 baseline:** `9301e5e`

---

## Overview

Production safety tooling prevents recurrence of the 2026-07-08 incident:

- Missing `.env` → backend crash on restart → 502 → empty UI
- Uncommitted code on production host → schema mismatch risk

Wave 1 adds **scripts and CLI checks** without changing Phase 8.1 runtime behavior.

---

## Components

### 1. `scripts/preflight-env.sh`

Checks `.env` file exists and is readable, then runs Python validation.

```bash
bash scripts/preflight-env.sh --check
bash scripts/preflight-env.sh --verbose
bash scripts/preflight-env.sh --check --with-schema   # + alembic vs DB
```

Modes:

| Flag | Purpose |
|------|---------|
| `--check` | Default read-only validation |
| `--systemd` | Compact output for systemd `ExecStartPre` (Wave 2) |
| `--verbose` | Extra diagnostics |
| `--with-schema` | Compare alembic head to `alembic_version` table |

Exit `0` = pass, `1` = fail.

### 2. `python -m app.ops.preflight`

Validates required environment variables using existing `validate_environment()`:

| Variable | Required |
|----------|----------|
| `DATABASE_URL` | Always |
| `SECRET_KEY` | Always |
| `ENVIRONMENT_MODE` | Always |
| `SUPABASE_URL` | When `ENVIRONMENT_MODE=MAIN` |

```bash
.venv/bin/python -m app.ops.preflight
.venv/bin/python -m app.ops.preflight --schema
```

**Not imported by API lifespan** — Phase 8.1 startup path unchanged.

### 3. `scripts/lib/deploy-guard.sh`

Blocks deploy when git working tree has unallowed changes.

```bash
source scripts/lib/deploy-guard.sh
deploy_guard_check /path/to/repo
deploy_guard_check_ram 300
```

Bypass flags:

| Variable | Effect |
|----------|--------|
| `DEPLOY_FORCE=1` | Bypass dirty tree and RAM checks |
| `DEPLOY_FORCE_DIRTY=1` | Bypass dirty tree only |
| `DEPLOY_FORCE_RAM=1` | Bypass RAM check only |

Skipped when `GITHUB_ACTIONS=true`.

**Allowlist** (exempt from dirty check):

- `frontend/tsconfig*.tsbuildinfo`
- `.coverage`, `htmlcov/`
- `.env.bak*`, `.env.local`, `.env.integration`
- `tmp_*`, investigation screenshots
- `frontend/test-results/`
- `docs/release/screenshots/`

### 4. `scripts/production-recovery.sh`

Assess-only recovery report (Wave 1):

```bash
bash scripts/production-recovery.sh --assess-only
```

No restarts, no git reset, no `.env` restore.

---

## ExecStartPre architecture (Wave 2)

Wave 2 wires `scripts/preflight-env.sh --systemd` into systemd **before** process start. Preflight is **fail-closed**: exit `1` prevents `ExecStart` from running.

| Unit | Repo file | ExecStartPre |
|------|-----------|--------------|
| Backend | `deploy/systemd/marketplace-backend.service` | `preflight-env.sh --systemd` |
| Worker | `deploy/systemd/marketplace-worker.service` | `preflight-env.sh --systemd` |
| Orchestrator | `deploy/systemd/marketplace-orchestrator.service` | `preflight-env.sh --systemd` |

**Flow (each restart / start):**

1. systemd loads `EnvironmentFile=-…/.env` (optional; missing file does not abort unit load).
2. `ExecStartPre` runs preflight: `.env` exists + readable → `.venv` present → `python -m app.ops.preflight` (no `--schema` in unit).
3. On success → `ExecStart` runs uvicorn / ETL worker / orchestration worker.
4. On failure → unit enters `failed`; journal shows `PREFLIGHT FAIL: …`.

**Not in ExecStartPre:** `--with-schema` (alembic vs DB) — remains manual ops / recovery procedure to avoid false blocks on DB blips or schema lag.

**API lifespan unchanged** — preflight is not imported by `app.main`; only systemd invokes the script.

**Deploy to VPS:** copy units to `/etc/systemd/system/`, `daemon-reload`, restart services (maintenance window). See [production_recovery_runbook.md](./production_recovery_runbook.md) Phase 4.

---

## Wave roadmap

| Wave | Scope | Production touch |
|------|-------|------------------|
| **1** | Scripts, CLI, docs, tests | **None** (done — `2e9aaad`) |
| **2** | systemd `ExecStartPre`, orchestrator unit in repo | **Restart required** (repo done; VPS pending) |
| **3** | Deploy guard in `deploy-frontend.sh` | Next deploy only |

---

## Operator checklist (daily)

```bash
bash scripts/preflight-env.sh --check
bash scripts/production-recovery.sh --assess-only
```

Before any deploy:

```bash
source scripts/lib/deploy-guard.sh && deploy_guard_check .
bash scripts/post_deploy_smoke_test.sh
```

---

## See also

- [production_recovery_runbook.md](./production_recovery_runbook.md)

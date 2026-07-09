# Production Safety (Phase 8.2.0 — 9.3A)

**Status:** Safety tooling certified (8.2–8.3); auth phases 9.1A–9.3A deployed to production runtime  
**Committed HEAD (VPS):** `b85854c` — Phase 9.2 platform admin  
**Alembic head (DB):** `0035_registration_invites` — Phase 9.3A invite system  
**CERTIFIED_SHA:** defined in `scripts/production-recovery.sh` — formal update in Phase 9.3X-C  
**Historical safety baseline:** `11731e9` — 8.2.1a recovery stabilization  
**Wave 2 deployed:** systemd `ExecStartPre` on production  
**Phase 8.1 historical rollback:** `9301e5e`

---

## Overview

Production safety tooling prevents recurrence of the 2026-07-08 incident:

- Missing `.env` → backend crash on restart → 502 → empty UI
- Uncommitted code on production host → schema mismatch risk

Phase 9.x adds auth/admin surfaces that must stay aligned with the database:

| Risk | Mitigation |
|------|------------|
| Code at HEAD without migration `0035` | `preflight --schema` / `alembic current` |
| Migration `0035` without invite code | ORM/import failures on restart |
| Dirty tree deploy | `deploy-guard.sh` blocks frontend build |
| Rollback to pre-9.3A code | Runbook Phase 3 — requires migration coordination |

---

## Auth & admin inventory (Phase 9.2B — 9.3A)

| Item | Detail |
|------|--------|
| **Roles** | `seller`, `platform_admin` (`users.role`, migration `0034`) |
| **Registration gate** | `REGISTRATION_MODE=invite_only` (Phase 9.1A) |
| **Invite system** | `registration_invites` table (migration `0035`) |
| **Admin users API** | `GET /api/v1/admin/users` — read-only (Phase 9.2C) |
| **Admin invites API** | `GET/POST/DELETE /api/v1/admin/invites` (Phase 9.3A) |
| **Frontend gates** | `RequirePlatformAdmin` on admin/ops/system routes (Phase 9.2) |
| **Admin UI** | Администрирование → Пользователи, Приглашения |

Environment variables for invites:

| Variable | Purpose |
|----------|---------|
| `REGISTRATION_MODE` | `invite_only` in production |
| `APP_PUBLIC_URL` | Base URL for `{APP_PUBLIC_URL}/register?invite=…` links |
| `INVITE_TOKEN_EXPIRE_HOURS` | Default TTL when creating invites (default `72`) |

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

**Expected schema head (current):** `0035_registration_invites`

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

**Not imported by API lifespan** — preflight is not part of normal request handling.

### 3. `scripts/lib/deploy-guard.sh`

Blocks deploy when git working tree has unallowed changes. **Wired into `scripts/deploy-frontend.sh` (Wave 3).**

```bash
source scripts/lib/deploy-guard.sh
deploy_guard_check /path/to/repo
deploy_guard_check_ram 300
```

Before frontend deploy (automatic in `deploy-frontend.sh`):

```bash
bash scripts/deploy-frontend.sh
# runs deploy_guard_check + deploy_guard_check_ram after flock, before build
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

**Note:** Phase 9.3A source files (`app/services/invite_service.py`, `alembic/versions/0035_*.py`, etc.) are **not** allowlisted — deploy guard blocks until committed (Phase 9.3X-C).

### 4. `scripts/production-recovery.sh`

Assess-only recovery report (Wave 1):

```bash
bash scripts/production-recovery.sh --assess-only
```

Compares `git rev-parse HEAD` to `CERTIFIED_SHA` in the script. During Phase 9.3X-B/C, a mismatch is expected until formal certification — see [production_recovery_runbook.md](./production_recovery_runbook.md).

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

## Deploy guard integration (Wave 3)

`scripts/deploy-frontend.sh` runs **fail-closed** checks immediately after acquiring the deploy lock:

1. `deploy_guard_check "${ROOT}"` — block if git tree has unallowed changes.
2. `deploy_guard_check_ram "${DEPLOY_MIN_FREE_MB}"` — block if available memory below threshold.

On failure the script exits **before** stopping preview, `npm run build`, or `rsync` to `/var/www/`.

| Check | Bypass |
|-------|--------|
| Dirty tree | `DEPLOY_FORCE_DIRTY=1` or `DEPLOY_FORCE=1` |
| Low RAM | `DEPLOY_FORCE_RAM=1` or `DEPLOY_FORCE=1` |
| CI | `GITHUB_ACTIONS=true` (tree check only) |

---

## Wave roadmap

| Wave | Scope | Production touch |
|------|-------|------------------|
| **1** | Scripts, CLI, docs, tests | **None** (done — `2e9aaad`) |
| **2** | systemd `ExecStartPre`, orchestrator unit | **Done** — deployed on VPS |
| **3** | Deploy guard in `deploy-frontend.sh` | **Active** — blocks dirty 9.3A deploy |

---

## Operator checklist (daily)

```bash
bash scripts/preflight-env.sh --check
bash scripts/production-recovery.sh --assess-only
```

Before any deploy:

```bash
bash scripts/preflight-env.sh --check
bash scripts/preflight-env.sh --check --with-schema
bash scripts/production-recovery.sh --assess-only
bash scripts/deploy-frontend.sh   # includes deploy guard (Wave 3)
bash scripts/post_deploy_smoke_test.sh
```

Post-deploy auth checks (see [production_recovery_runbook.md](./production_recovery_runbook.md) Phase 5).

---

## See also

- [production_recovery_runbook.md](./production_recovery_runbook.md)
- [../frontend/user_workflows.md](../frontend/user_workflows.md)
- [../release/README.md](../release/README.md)

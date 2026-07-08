# Production Safety (Phase 8.2.0)

**Status:** Wave 1 implemented (tooling only — not wired to systemd)  
**Baseline:** Phase 8.1 certified (`9301e5e`)

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
| `--systemd` | Compact output for future ExecStartPre (Wave 2) |
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

## Wave roadmap

| Wave | Scope | Production touch |
|------|-------|------------------|
| **1** (current) | Scripts, CLI, docs, tests | **None** |
| **2** | systemd `ExecStartPre`, orchestrator unit in repo | Restart required |
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

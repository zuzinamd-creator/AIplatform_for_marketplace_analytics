# Production Recovery Runbook

**Phase:** 8.2.0 — Production Safety  
**Certified baseline:** `9301e5e` (Phase 8.1)  
**Last updated:** 2026-07-08

> Human operator guide for restoring production after configuration or code incidents.  
> Wave 1 provides **assess-only** automation; destructive steps remain manual until Wave 2.

---

## When to use

- API returns **502 Bad Gateway**
- `marketplace-backend.service` failed after restart
- Missing `.env` or invalid environment variables
- Suspected uncommitted code on production host
- Schema mismatch (ORM fields without migration)

---

## Phase 0 — STOP

Do **not**:

- Run `git clean -fd` (may delete `.env.bak*` backups)
- Run `alembic upgrade` without explicit approval
- Deploy Invite Only or uncommitted features
- Delete PostgreSQL or Storage data

---

## Phase 1 — Assess (read-only)

```bash
cd /root/AIplatform_for_marketplace_analytics
bash scripts/production-recovery.sh --assess-only
bash scripts/preflight-env.sh --check --verbose
```

Record:

- `git rev-parse HEAD`
- `.env` exists and readable
- `/health` and `/health/ready` via HTTPS
- `python -m app.ops.preflight --schema` (if DB reachable)

---

## Phase 2 — Restore `.env`

If `.env` is missing:

```bash
cp /root/.env.bak.int2.recovery /root/AIplatform_for_marketplace_analytics/.env
chmod 600 /root/AIplatform_for_marketplace_analytics/.env
bash scripts/preflight-env.sh --check
```

Backup locations (in priority order):

1. `/root/.env.bak.int2.recovery`
2. `/root/AIplatform_for_marketplace_analytics/.env.bak.int2`

---

## Phase 3 — Restore code (manual, maintenance window)

Only if HEAD diverged from certified baseline:

```bash
git fetch origin
git reset --hard 9301e5e
# Remove uncommitted feature files if present (see incident RCA)
```

Verify:

```bash
.venv/bin/python -c "from app.main import app; print('import OK')"
```

---

## Phase 4 — Restart services (Wave 2+ only)

> **Not automated in Wave 1.** After Wave 2 systemd preflight is installed:

```bash
sudo systemctl daemon-reload
sudo systemctl restart marketplace-backend marketplace-worker marketplace-orchestrator
```

---

## Phase 5 — Smoke test

```bash
bash scripts/post_deploy_smoke_test.sh
```

Pilot tenant check (JWT or login):

- `GET /api/v1/reports` — expect ≥ 12 for pilot user
- `GET /api/v1/costs` — expect ≥ 1
- `GET /api/v1/system/persistence-status`

---

## Phase 6 — Verify data unchanged

Compare DB counts before/after recovery:

```sql
SELECT COUNT(*) FROM reports;
SELECT COUNT(*) FROM cost_history;
SELECT COUNT(*) FROM users;
```

Expected post-incident (2026-07-08): reports=31, cost_history=112, users=20.

---

## Phase 7 — Document

Log in incident record:

- Timeline (when `.env` lost, when restart occurred)
- Root cause
- Recovery actions taken
- Smoke test results

---

## Related

- [production_safety.md](./production_safety.md) — preflight and deploy guards
- [../ops/frontend-deploy.md](../ops/frontend-deploy.md) — frontend deploy
- [../release/phase_81_production_release.md](../release/phase_81_production_release.md) — certified baseline

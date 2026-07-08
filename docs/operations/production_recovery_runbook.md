# Production Recovery Runbook

**Phase:** 8.2.0 — Production Safety (8.2.1a ops stabilization)  
**Certified production baseline:** `01cfee9` — Wave 2 systemd preflight deployed  
**Historical rollback (Phase 8.1 only):** `9301e5e` — do not use for routine assess  
**Last updated:** 2026-07-08

> Human operator guide for restoring production after configuration or code incidents.  
> `scripts/production-recovery.sh` is **assess-only**; destructive steps remain manual.

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

Only if HEAD diverged from the **current** certified production baseline (`01cfee9`):

```bash
git fetch origin
git reset --hard 01cfee9
# Remove uncommitted feature files if present (see incident RCA)
```

**Historical rollback** to Phase 8.1 promotion-expenses MVP (emergency only, not routine assess):

```bash
git reset --hard 9301e5e
```

Verify:

```bash
.venv/bin/python -c "from app.main import app; print('import OK')"
```

---

## Phase 4 — Restart services

> Wave 2 systemd `ExecStartPre` is deployed on production. Use after unit or `.env` changes:

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

# Production Recovery Runbook

**Phase:** 9.3A — Auth & admin (runtime) · 8.2.1a — Production safety foundation  
**Committed HEAD (VPS):** `b85854c` — Phase 9.2 platform admin  
**Alembic head (DB):** `0035_registration_invites` — Phase 9.3A invite system  
**CERTIFIED_SHA:** see `scripts/production-recovery.sh` (formal update in Phase 9.3X-C — do not change during 9.3X-B)  
**Historical rollback (Phase 8.1 only):** `9301e5e` — emergency only  
**Historical safety baseline (8.2.1a):** `11731e9` — pre-auth phases  
**Last updated:** 2026-07-09

> Human operator guide for restoring production after configuration or code incidents.  
> `scripts/production-recovery.sh` is **assess-only**; destructive steps remain manual.

---

## Current platform state (Phase 9.x)

| Component | State |
|-----------|-------|
| **Roles** | `users.role`: `seller` (default) \| `platform_admin` (migration `0034`) |
| **Registration** | `REGISTRATION_MODE=invite_only` — invite link required for new accounts |
| **Invite table** | `registration_invites` (migration `0035`) — token hash, TTL, used/revoked timestamps |
| **Admin API** | `/api/v1/admin/users` (read-only), `/api/v1/admin/invites` (create/list/revoke) — `platform_admin` only |
| **Admin UI** | Администрирование → Пользователи, Приглашения |

**Important:** Production runtime currently includes **uncommitted Phase 9.3A** code in the working tree while migration `0035` is already applied. Rolling back code below 9.3A without a matching DB downgrade will cause schema mismatch.

---

## When to use

- API returns **502 Bad Gateway**
- `marketplace-backend.service` failed after restart
- Missing `.env` or invalid environment variables
- Suspected uncommitted code on production host
- Schema mismatch (ORM fields without migration)
- Invite registration or admin panel failures after deploy

---

## Phase 0 — STOP

Do **not**:

- Run `git clean -fd` (may delete `.env.bak*` backups and **untracked migration `0035` file**)
- Run `alembic upgrade` or `alembic downgrade` without explicit approval
- Roll back code to pre-9.3A while DB remains at `0035_registration_invites`
- Delete PostgreSQL or Storage data
- Revoke all pending invites without operator approval

---

## Phase 1 — Assess (read-only)

```bash
cd /root/AIplatform_for_marketplace_analytics
bash scripts/production-recovery.sh --assess-only
bash scripts/preflight-env.sh --check --verbose
bash scripts/preflight-env.sh --check --with-schema
```

Record:

- `git rev-parse HEAD`
- `git status --short` (uncommitted 9.3A files?)
- `.env` exists and readable (`REGISTRATION_MODE`, `APP_PUBLIC_URL`)
- `/health` and `/health/ready` via HTTPS
- `python -m app.ops.preflight --schema` → expect `0035_registration_invites`
- Auth smoke (no credentials in log):
  - `GET /api/v1/auth/registration-status` → `{"available":false}` when `invite_only`
  - `GET /api/v1/auth/invite/validate?token=…` → `valid` true/false

---

## Phase 2 — Restore `.env`

If `.env` is missing:

```bash
cp /root/.env.bak.int2.recovery /root/AIplatform_for_marketplace_analytics/.env
chmod 600 /root/AIplatform_for_marketplace_analytics/.env
bash scripts/preflight-env.sh --check
```

Verify auth-related keys:

| Variable | Production expectation |
|----------|---------------------|
| `REGISTRATION_MODE` | `invite_only` |
| `APP_PUBLIC_URL` | Public HTTPS origin (used in invite links) |
| `INVITE_TOKEN_EXPIRE_HOURS` | Default `72` |

Backup locations (in priority order):

1. `/root/.env.bak.int2.recovery`
2. `/root/AIplatform_for_marketplace_analytics/.env.bak.int2`

---

## Phase 3 — Restore code (manual, maintenance window)

### 3a — Routine assess mismatch (HEAD vs CERTIFIED_SHA)

If `production-recovery.sh` reports HEAD ≠ `CERTIFIED_SHA` but services are healthy:

- **Do not auto-reset** during Phase 9.3X-B/C transition.
- Document both SHAs; proceed to Phase 9.3X-C for formal certification.

### 3b — Code rollback (emergency)

**Pre-9.3A rollback is unsafe** while `alembic_version = 0035_registration_invites`. Options:

1. **Preferred:** restore to the certified commit that includes 9.3A (after Phase 9.3X-C commit).
2. **Emergency only:** downgrade migration `0035` **then** reset code — requires explicit DBA approval; see migration file `alembic/versions/0035_registration_invites.py`.

Historical safety baseline (pre-auth, **will break 9.x runtime**):

```bash
git fetch origin
git reset --hard 11731e9
# Only with matching alembic downgrade — not routine
```

Historical rollback to Phase 8.1 promotion-expenses MVP (emergency only):

```bash
git reset --hard 9301e5e
```

Verify:

```bash
.venv/bin/python -c "from app.main import app; print('import OK')"
.venv/bin/python -c "from app.services.invite_service import InviteService; print('invites OK')"
```

---

## Phase 4 — Restart services

> Wave 2 systemd `ExecStartPre` is deployed on production. Use after unit or `.env` changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart marketplace-backend marketplace-worker marketplace-orchestrator
```

Backend loads Python from the repo working tree — uncommitted 9.3A changes take effect on restart.

---

## Phase 5 — Smoke test

```bash
bash scripts/post_deploy_smoke_test.sh
```

Auth & admin checks (platform_admin JWT):

| Check | Expect |
|-------|--------|
| `GET /api/v1/admin/users` | 200, paginated list |
| `GET /api/v1/admin/invites` | 200, paginated list |
| `POST /api/v1/auth/register` (no token) | 403 when `invite_only` |

Pilot tenant check (seller JWT):

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
SELECT COUNT(*) FROM registration_invites;
SELECT version_num FROM alembic_version;
```

Expected alembic head: `0035_registration_invites`.

---

## Phase 7 — Document

Log in incident record:

- Timeline (when `.env` lost, when restart occurred)
- Root cause
- Recovery actions taken
- Smoke test results
- Whether invite/admin endpoints were validated

---

## Migration reference

| Revision | Phase | Purpose |
|----------|-------|---------|
| `0034_user_role_platform_admin` | 9.2B | `users.role` column, seed `platform_admin` |
| `0035_registration_invites` | 9.3A | `registration_invites` table + RLS lockdown |

Apply (only when approved):

```bash
.venv/bin/alembic upgrade head
```

Downgrade `0035` drops `registration_invites` — **data loss for pending invites**.

---

## Related

- [production_safety.md](./production_safety.md) — preflight and deploy guards
- [../ops/frontend-deploy.md](../ops/frontend-deploy.md) — frontend deploy
- [../release/README.md](../release/README.md) — Phase 9.x release index
- [../frontend/user_workflows.md](../frontend/user_workflows.md) — invite registration flow

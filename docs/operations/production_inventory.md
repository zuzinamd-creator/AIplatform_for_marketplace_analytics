# Production server inventory (pilot)

## Production code baseline (Phase 9.17-F)

| Field | Value |
|-------|-------|
| Git SHA | `f85dea6151cc8b222b4aa794d72fac1939c5f1cd` |
| Frontend bundle | `index-DVVPbWvu.js` (FE surface since 9.16-C) |
| Alembic | `0037_inv_stream_idx` |
| WWW root | `/var/www/marketplace-analytics` |
| Cert | [phase_917f_release_certification.md](../release/phase_917f_release_certification.md) |

## Services (systemd)

| Unit | Role |
|------|------|
| `marketplace-backend` | FastAPI / uvicorn :8000 |
| `marketplace-worker` | ETL queue consumer |
| `marketplace-orchestrator` | Runtime control plane — rebuild dispatch + maintenance (`app.runtime.orchestration_worker`) |
| `nginx` | HTTPS, static frontend, API proxy |
| `marketplace-dr-drill.timer` | Weekly backup drill (Sun 03:00 UTC) |

### `marketplace-orchestrator` (Phase 8.2.0 Wave 2)

| Property | Value |
|----------|-------|
| **Repo unit file** | `deploy/systemd/marketplace-orchestrator.service` |
| **Production path** | `/etc/systemd/system/marketplace-orchestrator.service` |
| **ExecStart** | `.venv/bin/python -m app.runtime.orchestration_worker` |
| **ExecStartPre** | `scripts/preflight-env.sh --systemd` (`.env` + env validation before start) |
| **Restart** | `on-failure` (singleton via PostgreSQL lease `orchestrator_primary`) |
| **Purpose** | Dispatches `snapshot_rebuild_requirements`, runs maintenance cycles; separate from ETL worker |

Backend and worker units use the same `ExecStartPre` preflight gate (Wave 2). See [production_safety.md](./production_safety.md).

## Monitoring

| Component | Access |
|-----------|--------|
| Uptime Kuma | `http://127.0.0.1:3001` (SSH tunnel) |
| Credentials | `/root/.uptime_kuma_credentials` (600) |

## Secrets (mode 600, not in git)

| File | Purpose |
|------|---------|
| `/root/AIplatform_for_marketplace_analytics/.env` | App config |
| `/root/.mvp_test_user_credentials` | E2E test user only |
| `/root/.marketplace_smtp_credentials` | SMTP (create before go-live) |
| `/root/.uptime_kuma_credentials` | Monitoring UI |

## Backups

| Path | Content |
|------|---------|
| `/root/backups/marketplace-drill/` | pg_dump + config tarballs |
| `/var/log/marketplace-drill/latest.log` | Last DR drill output |

## Post-deploy gate

```bash
bash scripts/post_deploy_smoke_test.sh    # PASS/FAIL
bash scripts/ops_readiness_checks.sh
python scripts/etl_pipeline_validation.py
```

## Dev-only scripts (keep in repo, do not schedule on prod)

- `scripts/profile_*.py`
- `scripts/ux2_real_data_validation.py`
- `scripts/seller_ai_validation.py`

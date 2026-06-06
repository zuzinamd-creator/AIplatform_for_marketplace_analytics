# Production server inventory (pilot)

## Services (systemd)

| Unit | Role |
|------|------|
| `marketplace-backend` | FastAPI / uvicorn :8000 |
| `marketplace-worker` | ETL queue consumer |
| `nginx` | HTTPS, static frontend, API proxy |
| `marketplace-dr-drill.timer` | Weekly backup drill (Sun 03:00 UTC) |

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

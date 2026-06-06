# Uptime Kuma — MVP monitoring

## Install

```bash
cd deploy/uptime-kuma
docker compose up -d
```

UI: `http://127.0.0.1:3001` (SSH tunnel from laptop: `ssh -L 3001:127.0.0.1:3001 root@321997.fornex.cloud`)

## Recommended monitors

| Name | URL | Interval |
|------|-----|----------|
| API liveness | `https://321997.fornex.cloud/health` | 60s |
| API readiness | `https://321997.fornex.cloud/health/ready` | 60s |
| Frontend | `https://321997.fornex.cloud/` | 120s |

Expected keyword for health: `"status":"ok"` / `"status":"ready"`

## Notifications

1. Open Uptime Kuma → **Settings → Notifications**
2. Add **Email (SMTP)** using same Mail.ru credentials as the app, or **Telegram** bot
3. Attach notification to each monitor

## Verify

```bash
docker ps --filter name=marketplace-uptime-kuma
curl -s http://127.0.0.1:3001 | head -c 80
```

## Stop

```bash
docker compose -f deploy/uptime-kuma/docker-compose.yml down
```

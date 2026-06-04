# Frontend deploy & RAM safety (2 GB VPS)

Production UI is served by **nginx** from `/var/www/marketplace-analytics`.  
`marketplace-frontend.service` (Vite preview on port 4173) is **optional** — disable it on VPS to save RAM.

## One-command deploy

```bash
cd /root/AIplatform_for_marketplace_analytics && bash scripts/deploy-frontend.sh
```

First time (or after pulling unit files):

```bash
sudo bash scripts/install-frontend-ops.sh
sudo systemctl disable --now marketplace-frontend.service   # recommended on production
```

## What the deploy script does

1. Exclusive lock (`/var/lock/marketplace-frontend-deploy.lock`) — no parallel deploys.
2. Stops `marketplace-frontend.service` if running.
3. Kills stuck **project** Node workers (vite/tsc/npm), not IDE processes.
4. Checks **available** RAM (`free -m`); aborts if &lt; 300 MB unless `DEPLOY_FORCE=1`.
5. Builds with `NODE_OPTIONS=--max-old-space-size=1024`.
6. Publishes `dist/` to nginx root.
7. Restarts preview **only** if the systemd unit is **enabled**.

## Low memory / force build

```bash
DEPLOY_FORCE=1 bash scripts/deploy-frontend.sh
DEPLOY_MIN_FREE_MB=400 bash scripts/deploy-frontend.sh
NODE_BUILD_HEAP_MB=768 bash scripts/deploy-frontend.sh
```

## Daily cleanup (systemd timer)

Installs with `install-frontend-ops.sh`:

- **Timer:** `marketplace-frontend-cleanup.timer` — daily ~04:15
- **Action:** trims npm cache, vite temp, old npm logs when over limits

Manual run:

```bash
bash scripts/cleanup-frontend-artifacts.sh
bash scripts/cleanup-frontend-artifacts.sh --quick
```

## systemd unit highlights

| Setting | Purpose |
|--------|---------|
| `Restart=on-failure` | No restart loop on clean exit |
| `StartLimitBurst=5` | Limits rapid restart storms |
| `MemoryMax=400M` | Preview cannot eat entire VPS |
| `ExecStartPre=fuser -k 4173/tcp` | No duplicate preview on same port |
| `ExecStartPre=cleanup --quick` | Trim vite temp before start |

## Audit checklist

```bash
systemctl status marketplace-frontend.service
systemctl is-enabled marketplace-frontend.service   # prefer disabled on prod
pgrep -af 'AIplatform_for_marketplace_analytics/frontend' | grep -v cursor || true
free -m
```

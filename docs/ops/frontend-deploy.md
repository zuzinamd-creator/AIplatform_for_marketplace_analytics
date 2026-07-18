# Frontend deploy & RAM safety (2 GB VPS)

Production UI is served by **nginx** from `/var/www/marketplace-analytics`.  
`marketplace-frontend.service` (Vite preview on port 4173) is **optional** — disable it on VPS to save RAM.

**Current production FE (Phase 9.16-C):** commit `7f65cfb` · bundle `index-DVVPbWvu.js` · certified [phase_916c_production_baseline.md](../release/phase_916c_production_baseline.md).

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
2. **Deploy guard** (`scripts/lib/deploy-guard.sh`): blocks if git tree has unallowed changes; checks available RAM (default ≥ 300 MB). Bypass: `DEPLOY_FORCE_DIRTY=1`, `DEPLOY_FORCE_RAM=1`, or `DEPLOY_FORCE=1`.
3. Stops `marketplace-frontend.service` if running.
4. Kills stuck **project** Node workers (vite/tsc/npm), not IDE processes.
5. Builds with `NODE_OPTIONS=--max-old-space-size=1024`.
6. Publishes `dist/` to nginx root.
7. Restarts preview **only** if the systemd unit is **enabled**.

Allowlisted dirty paths (do not block): `frontend/tsconfig*.tsbuildinfo`, `.coverage`, `tmp_*`, test artifacts. See [production_safety.md](../operations/production_safety.md).

## Low memory / force build

```bash
DEPLOY_FORCE=1 bash scripts/deploy-frontend.sh          # bypass tree + RAM guards
DEPLOY_FORCE_DIRTY=1 bash scripts/deploy-frontend.sh    # emergency dirty-tree deploy
DEPLOY_FORCE_RAM=1 bash scripts/deploy-frontend.sh      # emergency low-RAM deploy
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

#!/usr/bin/env bash
# Build Vite production bundle and publish to nginx document root.
# Safe on 2 GB RAM: stops preview service, frees project Node workers, checks memory.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WWW_ROOT="${WWW_ROOT:-/var/www/marketplace-analytics}"
FRONTEND_DIR="$ROOT/frontend"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-marketplace-frontend.service}"
DEPLOY_MIN_FREE_MB="${DEPLOY_MIN_FREE_MB:-300}"
LOCK_FILE="${LOCK_FILE:-/var/lock/marketplace-frontend-deploy.lock}"
NODE_BUILD_HEAP_MB="${NODE_BUILD_HEAP_MB:-1024}"

mkdir -p "$(dirname "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  echo "ERROR: Another frontend deploy is already running (lock: ${LOCK_FILE})." >&2
  exit 1
fi

_stop_project_node_workers() {
  local patterns=(
    "${ROOT}/frontend/node_modules/.bin/vite"
    "${ROOT}/frontend/node_modules/.bin/tsc"
    "${ROOT}/frontend/node_modules/typescript/bin/tsc"
    "npm run preview"
    "npm run build"
    "npm run dev"
  )
  for pat in "${patterns[@]}"; do
    pkill -f "$pat" 2>/dev/null || true
  done
}

echo "=== Pre-deploy: stop ${FRONTEND_SERVICE}, free Node RAM ==="
if systemctl list-unit-files "${FRONTEND_SERVICE}" &>/dev/null; then
  if systemctl is-active --quiet "${FRONTEND_SERVICE}" 2>/dev/null; then
    systemctl stop "${FRONTEND_SERVICE}" || true
  fi
fi
_stop_project_node_workers
sleep 2
_stop_project_node_workers

avail_mb="$(free -m | awk '/^Mem:/{print $7}')"
echo "Available memory: ${avail_mb} MB (minimum recommended: ${DEPLOY_MIN_FREE_MB} MB)"
if [[ "${avail_mb}" -lt "${DEPLOY_MIN_FREE_MB}" ]]; then
  echo "WARNING: Low memory (${avail_mb} MB < ${DEPLOY_MIN_FREE_MB} MB). Build may OOM and drop SSH." >&2
  echo "Stop optional services (preview, dev servers) or add swap before continuing." >&2
  if [[ "${DEPLOY_FORCE:-0}" != "1" ]]; then
    echo "Aborting. Set DEPLOY_FORCE=1 to build anyway." >&2
    exit 1
  fi
  echo "DEPLOY_FORCE=1 — continuing despite low memory."
fi

cd "$FRONTEND_DIR"

export VITE_API_BASE_URL=""
export VITE_API_PREFIX="/api/v1"
export NODE_OPTIONS="--max-old-space-size=${NODE_BUILD_HEAP_MB}"

echo "Building frontend (NODE_OPTIONS=${NODE_OPTIONS}, same-origin /api/v1 via nginx)..."
npm run build

echo "Publishing to ${WWW_ROOT} ..."
install -d -o www-data -g www-data -m 0755 "$WWW_ROOT"
rsync -a --delete "${FRONTEND_DIR}/dist/" "${WWW_ROOT}/"
chown -R www-data:www-data "$WWW_ROOT"

# Light post-build cleanup (vite temp from build)
"${ROOT}/scripts/cleanup-frontend-artifacts.sh" --quick || true

if systemctl is-enabled --quiet "${FRONTEND_SERVICE}" 2>/dev/null; then
  echo "Starting ${FRONTEND_SERVICE} (unit is enabled)..."
  systemctl start "${FRONTEND_SERVICE}" || true
else
  echo "Note: ${FRONTEND_SERVICE} is disabled — production UI is nginx only (recommended on 2 GB VPS)."
fi

echo "Deployed. Verify:"
echo "  curl -s http://127.0.0.1/ | grep -E 'lang=|body class'"
ls -la "${WWW_ROOT}/index.html"

#!/usr/bin/env bash
# Trim npm/vite temp and logs when they exceed limits (safe on 2 GB VPS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$ROOT/frontend"
QUICK=0
MAX_NPM_CACHE_MB="${MAX_NPM_CACHE_MB:-200}"
MAX_FRONTEND_LOG_MB="${MAX_FRONTEND_LOG_MB:-50}"

usage() {
  echo "Usage: $0 [--quick]"
  echo "  --quick  only vite/esbuild temp + stale preview port (for systemd ExecStartPre)"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick) QUICK=1; shift ;;
    -h | --help) usage ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
done

_dir_size_mb() {
  local path="$1"
  if [[ -d "$path" ]]; then
    du -sm "$path" 2>/dev/null | awk '{print $1}'
  else
    echo 0
  fi
}

_trim_dir_if_over() {
  local path="$1" limit_mb="$2" label="$3"
  local size
  size="$(_dir_size_mb "$path")"
  if [[ "$size" -gt "$limit_mb" ]]; then
    echo "Cleanup: ${label} ${size}MB > ${limit_mb}MB — removing ${path}"
    rm -rf "$path"
  fi
}

echo "=== Frontend artifact cleanup (quick=${QUICK}) ==="

# Vite / esbuild caches under project
_trim_dir_if_over "${FRONTEND_DIR}/node_modules/.vite" 100 "vite cache"
_trim_dir_if_over "${FRONTEND_DIR}/.vite" 50 "vite project cache"
find "${FRONTEND_DIR}/node_modules/.cache" -maxdepth 1 -type f -mtime +3 -delete 2>/dev/null || true

# Old npm debug logs in frontend tree
find "$FRONTEND_DIR" -maxdepth 2 -name 'npm-debug.log*' -mtime +7 -delete 2>/dev/null || true

if [[ "$QUICK" -eq 1 ]]; then
  exit 0
fi

# npm cache (global)
if command -v npm >/dev/null 2>&1; then
  cache_dir="$(npm config get cache 2>/dev/null || echo "${HOME}/.npm")"
  cache_mb="$(_dir_size_mb "$cache_dir")"
  if [[ "$cache_mb" -gt "$MAX_NPM_CACHE_MB" ]]; then
    echo "Cleanup: npm cache ${cache_mb}MB > ${MAX_NPM_CACHE_MB}MB"
    npm cache clean --force 2>/dev/null || rm -rf "${cache_dir:?}"/*
  fi
  log_dir="${HOME}/.npm/_logs"
  log_mb="$(_dir_size_mb "$log_dir")"
  if [[ "$log_mb" -gt "$MAX_FRONTEND_LOG_MB" ]]; then
    echo "Cleanup: npm logs ${log_mb}MB — truncating ${log_dir}"
    find "$log_dir" -type f -mtime +3 -delete 2>/dev/null || true
  fi
fi

# System temp left by vite/esbuild (project-scoped names only)
find /tmp -maxdepth 1 \( -name 'vite-*' -o -name 'esbuild-*' \) -mtime +1 -user "$(id -un)" -exec rm -rf {} + 2>/dev/null || true

echo "Cleanup done."

#!/usr/bin/env bash
# Preflight: .env file presence/readability + optional Python env validation.
# Wave 1 — not wired into systemd ExecStartPre (Wave 2).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
PYTHON="${ROOT}/.venv/bin/python"
MODE="check"
WITH_SCHEMA=0
VERBOSE=0

usage() {
  cat <<'EOF'
Usage: scripts/preflight-env.sh [--check|--systemd|--verbose] [--with-schema]

  --check     Read-only checks (default)
  --systemd   Compact stderr output for systemd ExecStartPre (Wave 2)
  --verbose   Print diagnostic details
  --with-schema  Also run alembic head vs DB revision check (read-only)
EOF
}

log() {
  if [[ "${MODE}" == "verbose" || "${VERBOSE}" -eq 1 ]]; then
    echo "$@"
  fi
}

fail() {
  echo "PREFLIGHT FAIL: $*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) MODE="check" ;;
    --systemd) MODE="systemd" ;;
    --verbose) MODE="verbose"; VERBOSE=1 ;;
    --with-schema) WITH_SCHEMA=1 ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
  shift
done

log "root=${ROOT}"
log "env_file=${ENV_FILE}"

if [[ ! -f "${ENV_FILE}" ]]; then
  fail "missing ${ENV_FILE} (restore from backup before restart)"
fi

if [[ ! -r "${ENV_FILE}" ]]; then
  fail "unreadable ${ENV_FILE}"
fi

log "env file ok"

if [[ ! -x "${PYTHON}" ]]; then
  fail "python venv not found at ${PYTHON}"
fi

SCHEMA_ARGS=()
if [[ "${WITH_SCHEMA}" -eq 1 ]]; then
  SCHEMA_ARGS+=(--schema)
fi

if ! (cd "${ROOT}" && "${PYTHON}" -m app.ops.preflight "${SCHEMA_ARGS[@]}"); then
  fail "environment validation failed (see messages above)"
fi

if [[ "${MODE}" == "verbose" ]]; then
  echo "PREFLIGHT OK: ${ENV_FILE}"
fi

exit 0

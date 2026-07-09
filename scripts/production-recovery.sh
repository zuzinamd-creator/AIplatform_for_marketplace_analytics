#!/usr/bin/env bash
# Production recovery — assess-only. No destructive actions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BASE_HTTPS:-https://321997.fornex.cloud}"
API="${BASE}/api/v1"
CERTIFIED_SHA="${CERTIFIED_SHA:-74e7fff65664d4cc87118b621b2dc8221c1bf09e}"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
BACKUP_ENV="${BACKUP_ENV:-/root/.env.bak.int2.recovery}"

FAILURES=0
WARNINGS=0

pass() { echo "  OK   $*"; }
warn() { echo "  WARN $*"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo "  FAIL $*"; FAILURES=$((FAILURES + 1)); }

usage() {
  cat <<'EOF'
Usage: scripts/production-recovery.sh [--assess-only]

  --assess-only   Read-only assessment (default, only mode in Wave 1)

No restarts, no git reset, no .env restore — report only.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --assess-only) ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1 (Wave 1 supports --assess-only only)" >&2; exit 2 ;;
  esac
  shift
done

echo "=== Production Recovery Assessment (read-only) ==="
echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "host: $(hostname -f 2>/dev/null || hostname)"
echo "certified_sha: ${CERTIFIED_SHA}"
echo ""

echo "--- Git baseline ---"
HEAD="$(cd "${ROOT}" && git rev-parse HEAD 2>/dev/null || echo unknown)"
if [[ "${HEAD}" == "${CERTIFIED_SHA}"* || "${HEAD}" == "${CERTIFIED_SHA}" ]]; then
  pass "HEAD matches certified baseline (${HEAD:0:12})"
else
  fail "HEAD ${HEAD:0:12} != certified ${CERTIFIED_SHA:0:12}"
fi

DIRTY_COUNT="$(cd "${ROOT}" && git status --porcelain | wc -l | tr -d ' ')"
if [[ "${DIRTY_COUNT}" -eq 0 ]]; then
  pass "git working tree clean"
else
  warn "git working tree has ${DIRTY_COUNT} porcelain entries (review before deploy)"
fi

echo ""
echo "--- Environment file ---"
if [[ -f "${ENV_FILE}" ]]; then
  pass ".env exists at ${ENV_FILE}"
  if [[ -r "${ENV_FILE}" ]]; then
    pass ".env readable"
  else
    fail ".env not readable"
  fi
else
  fail ".env missing at ${ENV_FILE}"
fi

if [[ -f "${BACKUP_ENV}" ]]; then
  pass "backup env present at ${BACKUP_ENV}"
else
  warn "backup env missing at ${BACKUP_ENV}"
fi

if [[ -f "${ROOT}/scripts/preflight-env.sh" ]]; then
  if bash "${ROOT}/scripts/preflight-env.sh" --check 2>/dev/null; then
    pass "preflight-env.sh --check"
  else
    fail "preflight-env.sh --check"
  fi
else
  warn "scripts/preflight-env.sh not found"
fi

echo ""
echo "--- Process health (no systemctl in Wave 1) ---"
if curl -sk -o /dev/null -w "%{http_code}" "${BASE}/health" 2>/dev/null | grep -q 200; then
  pass "backend reachable via /health"
else
  fail "backend /health not OK"
fi

echo ""
echo "--- API health (HTTPS) ---"
for path in /health /health/ready; do
  body="$(curl -sk "${BASE}${path}" 2>/dev/null || true)"
  if echo "${body}" | grep -q '"status"'; then
    pass "${path} via nginx"
  else
    fail "${path} unreachable or invalid (${body:0:80})"
  fi
done

echo ""
echo "--- Alembic (code head) ---"
if [[ -x "${ROOT}/.venv/bin/alembic" ]]; then
  # Note: alembic 1.18.x rejects "heads -q" (-q is global-only). Use "heads" and never
  # abort the assess report on alembic CLI failure (set -e + pipefail).
  HEAD_REV="$(
    "${ROOT}/.venv/bin/alembic" heads 2>/dev/null | awk '{print $1}' | head -1 || true
  )"
  if [[ -n "${HEAD_REV}" ]]; then
    pass "alembic code head=${HEAD_REV}"
  else
    fail "alembic heads unavailable or empty"
  fi
else
  warn "alembic not found in venv"
fi

echo ""
echo "--- Schema check (optional, read-only) ---"
if [[ -f "${ENV_FILE}" && -x "${ROOT}/.venv/bin/python" ]]; then
  if (cd "${ROOT}" && "${ROOT}/.venv/bin/python" -m app.ops.preflight --schema 2>/dev/null); then
    pass "preflight --schema (code head matches DB alembic_version)"
  else
    warn "preflight --schema failed or DB unreachable (non-fatal in assess-only)"
  fi
else
  warn "schema check skipped (.env or python missing)"
fi

echo ""
echo "--- Deploy guard (dry) ---"
if [[ -f "${ROOT}/scripts/lib/deploy-guard.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/scripts/lib/deploy-guard.sh"
  if deploy_guard_check "${ROOT}"; then
    pass "deploy guard (tree allowlist)"
  else
    warn "deploy guard would block deploy (dirty tree)"
  fi
else
  warn "deploy-guard.sh not found"
fi

echo ""
echo "=== Assessment summary ==="
echo "  failures: ${FAILURES}"
echo "  warnings: ${WARNINGS}"
if [[ "${FAILURES}" -gt 0 ]]; then
  echo "  result: NEEDS ATTENTION"
  exit 1
fi
echo "  result: ASSESS OK (review warnings)"
exit 0

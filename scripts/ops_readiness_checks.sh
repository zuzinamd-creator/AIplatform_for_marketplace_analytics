#!/usr/bin/env bash
# Production ops readiness: security hardening, operational health, monitoring, backup validation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_HTTPS="${BASE_HTTPS:-https://321997.fornex.cloud}"
API="${BASE_HTTPS}/api/v1"
BACKUP_DIR="${BACKUP_DIR:-/root/backups/marketplace-drill}"
MAX_BACKUP_AGE_DAYS="${MAX_BACKUP_AGE_DAYS:-7}"
MIN_BACKUP_BYTES="${MIN_BACKUP_BYTES:-1048576}"
CREDS_FILE="${MVP_TEST_CREDS:-/root/.mvp_test_user_credentials}"
EMAIL="${TEST_EMAIL:-mvp-e2e-test@mail.ru}"
PASS="${TEST_PASS:-}"

FAILURES=0
WARNINGS=0

pass() { echo "  OK   $*"; }
warn() { echo "  WARN $*"; WARNINGS=$((WARNINGS + 1)); }
fail() { echo "  FAIL $*"; FAILURES=$((FAILURES + 1)); }

if [[ -z "${PASS}" && -f "${CREDS_FILE}" ]]; then
  PASS="$(grep '^password=' "${CREDS_FILE}" | cut -d= -f2-)"
fi

TOKEN=""
if [[ -n "${PASS}" ]]; then
  LOGIN_JSON=$(curl -sk -X POST "${API}/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "username=${EMAIL}&password=${PASS}" 2>/dev/null || true)
  TOKEN=$(echo "${LOGIN_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)
fi

echo "=== 1. Security hardening ==="

code=$(curl -sk -o /dev/null -w "%{http_code}" -I "http://321997.fornex.cloud/" | head -1)
if [[ "${code}" == "301" || "${code}" == "308" ]]; then
  pass "HTTP→HTTPS redirect (${code})"
else
  fail "HTTP→HTTPS redirect expected 301, got ${code}"
fi

hsts=$(curl -skI "${BASE_HTTPS}/" | grep -i strict-transport-security || true)
if [[ -n "${hsts}" ]]; then
  pass "HSTS header present"
else
  fail "Strict-Transport-Security header missing on ${BASE_HTTPS}/"
fi

for hdr in X-Content-Type-Options X-Frame-Options Referrer-Policy; do
  if curl -skI "${BASE_HTTPS}/" | grep -qi "^${hdr}:"; then
    pass "${hdr} present"
  else
    warn "${hdr} missing (recommended)"
  fi
done

cert_file="/etc/letsencrypt/live/321997.fornex.cloud/fullchain.pem"
if [[ -f "${cert_file}" ]]; then
  exp_epoch=$(openssl x509 -in "${cert_file}" -noout -enddate 2>/dev/null | cut -d= -f2 | xargs -I{} date -d "{}" +%s)
  now_epoch=$(date +%s)
  days_left=$(( (exp_epoch - now_epoch) / 86400 ))
  if [[ "${days_left}" -ge 30 ]]; then
    pass "TLS cert expires in ${days_left} days"
  else
    warn "TLS cert expires in ${days_left} days (<30)"
  fi
else
  warn "TLS cert not found at ${cert_file}"
fi

code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer invalid.token" "${API}/auth/me")
[[ "${code}" == "401" ]] && pass "invalid JWT rejected (401)" || fail "invalid JWT expected 401, got ${code}"

if [[ -f "${ROOT}/.env" ]]; then
  while IFS= read -r line; do
    case "${line}" in
      ENV_OK:*) pass "${line#ENV_OK:}" ;;
      ENV_ERROR:*) fail "${line#ENV_ERROR:}" ;;
      ENV_WARN:*) warn "${line#ENV_WARN:}" ;;
    esac
  done < <(
    cd "${ROOT}"
    PYTHONPATH="${ROOT}" "${ROOT}/.venv/bin/python3" - <<'PY'
import sys
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        import os
        os.environ.setdefault(k, v)
from app.core.startup_validation import validate_environment
from app.services.email_service import smtp_configured

report = validate_environment()
for e in report.errors:
    print(f"ENV_ERROR:{e}")
for w in report.warnings:
    print(f"ENV_WARN:{w}")
if report.ok:
    print("ENV_OK:startup validation passed")
else:
    sys.exit(1)
if not smtp_configured():
    print("ENV_WARN:SMTP_FROM unset — password reset emails unavailable")
PY
  )
else
  warn ".env not found — env validation skipped"
fi

if [[ -n "${PASS}" ]]; then
  triggered=0
  for i in $(seq 1 12); do
    code=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "${API}/auth/login" \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      -d 'username=rate.limit@test&password=wrong')
    if [[ "${code}" == "429" ]]; then
      pass "auth rate limit triggers 429 (attempt ${i})"
      triggered=1
      break
    fi
  done
  [[ "${triggered}" -eq 1 ]] || warn "auth rate limit did not return 429 in 12 attempts"
else
  warn "rate limit check skipped (set TEST_PASS or ${CREDS_FILE})"
fi

echo ""
echo "=== 2. Operational readiness ==="

for unit in marketplace-backend marketplace-worker nginx; do
  if systemctl is-active --quiet "${unit}" 2>/dev/null; then
    pass "systemd ${unit} active"
  else
    fail "systemd ${unit} not active"
  fi
done

for path in /health /health/ready; do
  body=$(curl -sk "${BASE_HTTPS}${path}")
  if echo "${body}" | grep -q '"status"'; then
    pass "${path} reachable via HTTPS"
  else
    fail "${path} not proxied correctly (expected JSON, got HTML or error)"
  fi
done

if command -v alembic >/dev/null 2>&1 || [[ -x "${ROOT}/.venv/bin/alembic" ]]; then
  ALEMBIC="${ROOT}/.venv/bin/alembic"
  head=$("${ALEMBIC}" heads 2>/dev/null | tail -1 | awk '{print $1}')
  current=$("${ALEMBIC}" current 2>/dev/null | tail -1 | awk '{print $1}')
  if [[ -n "${head}" && "${head}" == "${current}" ]]; then
    pass "alembic at head (${current})"
  else
    fail "alembic drift: current=${current:-none} head=${head:-unknown}"
  fi
else
  warn "alembic not found — migration check skipped"
fi

echo ""
echo "=== 3. Monitoring ==="

ready_ms=$(curl -sk -o /dev/null -w "%{time_total}" "${BASE_HTTPS}/health/ready")
ready_ms_int=$(python3 -c "print(int(float('${ready_ms}') * 1000))")
if [[ "${ready_ms_int}" -lt 2000 ]]; then
  pass "/health/ready latency ${ready_ms_int}ms"
else
  warn "/health/ready slow: ${ready_ms_int}ms"
fi

if [[ -n "${TOKEN}" ]]; then
  health_json=$(curl -sk -H "Authorization: Bearer ${TOKEN}" "${API}/ops/runtime/health")
    severity=$(echo "${health_json}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('overall_severity',''))" 2>/dev/null || echo "")
    if [[ "${severity}" == "ok" ]]; then
      pass "ops/runtime/health severity=ok"
    elif [[ -n "${severity}" ]]; then
      warn "ops/runtime/health severity=${severity}"
    else
      fail "ops/runtime/health unreachable or invalid JSON"
    fi

    summary_code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${API}/ops/runtime/summary")
    [[ "${summary_code}" == "200" ]] && pass "ops/runtime/summary → 200" || fail "ops/runtime/summary → ${summary_code}"

    cid=$(curl -skI -H "Authorization: Bearer ${TOKEN}" "${API}/auth/me" | grep -i x-correlation-id || true)
    [[ -n "${cid}" ]] && pass "X-Correlation-Id header present" || warn "X-Correlation-Id header missing"
elif [[ -n "${PASS}" ]]; then
  warn "monitoring auth skipped (login failed)"
else
  warn "ops monitoring checks skipped (set TEST_PASS)"
fi

if journalctl -u marketplace-backend --since "5 min ago" --no-pager 2>/dev/null | grep -q http_request; then
  pass "structured http_request logs in journal (last 5m)"
else
  warn "no recent structured http_request logs (idle or LOG_LEVEL)"
fi

echo ""
echo "=== 4. Backup validation ==="

latest_dump=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'postgres-*.dump' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
if [[ -z "${latest_dump}" ]]; then
  fail "no postgres-*.dump in ${BACKUP_DIR} — run scripts/dr_restore_drill.sh"
else
  size=$(stat -c '%s' "${latest_dump}")
  age_days=$(python3 -c "import os,time; print(int((time.time()-os.path.getmtime('${latest_dump}'))/86400))")
  pass "latest dump: $(basename "${latest_dump}") (${size} bytes, ${age_days}d old)"
  if [[ "${size}" -lt "${MIN_BACKUP_BYTES}" ]]; then
    fail "dump smaller than ${MIN_BACKUP_BYTES} bytes — likely failed pg_dump"
  else
    pass "dump size above minimum (${MIN_BACKUP_BYTES} bytes)"
  fi
  if [[ "${age_days}" -le "${MAX_BACKUP_AGE_DAYS}" ]]; then
    pass "dump age within ${MAX_BACKUP_AGE_DAYS} days"
  else
    warn "dump is ${age_days} days old (threshold ${MAX_BACKUP_AGE_DAYS}d) — re-run dr_restore_drill.sh"
  fi
  if command -v pg_restore >/dev/null 2>&1; then
    obj_count=$(pg_restore --list "${latest_dump}" 2>/dev/null | wc -l)
    if [[ "${obj_count}" -gt 10 ]]; then
      pass "pg_restore --list: ${obj_count} objects"
    else
      fail "pg_restore --list failed or dump corrupt (${obj_count} objects)"
    fi
  else
    warn "pg_restore not installed — integrity list check skipped"
  fi
fi

config_tar=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'app-config-*.tar.gz' -type f 2>/dev/null | head -1)
[[ -n "${config_tar}" ]] && pass "app-config snapshot present" || warn "no app-config tarball — run dr_restore_drill.sh"

echo ""
echo "=== Summary ==="
echo "  failures: ${FAILURES}"
echo "  warnings: ${WARNINGS}"
if [[ "${FAILURES}" -gt 0 ]]; then
  echo "  result: NOT READY"
  exit 1
fi
echo "  result: READY (review warnings)"
exit 0

#!/usr/bin/env bash
# Post-deploy smoke test — single PASS/FAIL gate for production.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${BASE_HTTPS:-https://321997.fornex.cloud}"
API="${BASE}/api/v1"
CREDS="${MVP_TEST_CREDS:-/root/.mvp_test_user_credentials}"
EMAIL="${TEST_EMAIL:-mvp-e2e-test@mail.ru}"
PASS="${TEST_PASS:-}"

FAILURES=0
pass() { echo "  OK   $*"; }
fail() { echo "  FAIL $*"; FAILURES=$((FAILURES + 1)); }

if [[ -z "${PASS}" && -f "${CREDS}" ]]; then
  PASS="$(grep '^password=' "${CREDS}" | cut -d= -f2-)"
fi

echo "=== Post-deploy smoke test ==="
echo "base=${BASE}"
echo ""

echo "--- Infrastructure ---"
for unit in marketplace-backend marketplace-worker nginx; do
  if systemctl is-active --quiet "${unit}" 2>/dev/null; then
    pass "systemd ${unit}"
  else
    fail "systemd ${unit} not active"
  fi
done

echo ""
echo "--- Health endpoints ---"
for path in /health /health/ready; do
  body=$(curl -sk "${BASE}${path}" 2>/dev/null || true)
  if echo "${body}" | grep -q '"status"'; then
    pass "${path}"
  else
    fail "${path} (expected JSON status)"
  fi
done

echo ""
echo "--- Auth & API ---"
if [[ -z "${PASS}" ]]; then
  fail "login skipped (no TEST_PASS / ${CREDS})"
else
  LOGIN_JSON=$(curl -sk -X POST "${API}/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d "username=${EMAIL}&password=${PASS}" 2>/dev/null || true)
  TOKEN=$(echo "${LOGIN_JSON}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)
  if [[ -n "${TOKEN}" ]]; then
    pass "login"
  else
    fail "login (${LOGIN_JSON:0:120})"
    TOKEN=""
  fi
fi

if [[ -n "${TOKEN:-}" ]]; then
  code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${API}/auth/me")
  [[ "${code}" == "200" ]] && pass "GET /auth/me" || fail "GET /auth/me → ${code}"

  code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${API}/reports?limit=5")
  [[ "${code}" == "200" ]] && pass "GET /reports" || fail "GET /reports → ${code}"

  code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" "${API}/costs")
  [[ "${code}" == "200" ]] && pass "GET /costs" || fail "GET /costs → ${code}"

  MP=wildberries
  code=$(curl -sk -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
    "${API}/dashboard/summary?marketplace=${MP}&start=2025-01-01&end=2025-12-31")
  [[ "${code}" == "200" ]] && pass "GET /dashboard/summary" || fail "GET /dashboard/summary → ${code}"
fi

echo ""
echo "--- Frontend ---"
code=$(curl -sk -o /dev/null -w "%{http_code}" "${BASE}/")
[[ "${code}" == "200" ]] && pass "GET / (frontend)" || fail "GET / → ${code}"

echo ""
echo "=== RESULT ==="
if [[ "${FAILURES}" -eq 0 ]]; then
  echo "PASS"
  exit 0
fi
echo "FAIL (${FAILURES} checks failed)"
exit 1

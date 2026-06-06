#!/usr/bin/env bash
# MVP readiness checks: HTTPS auth, rate limits, dashboard, reports cache.
set -euo pipefail

BASE_HTTPS="${BASE_HTTPS:-https://321997.fornex.cloud}"
API="${BASE_HTTPS}/api/v1"
# Never default to production accounts. Use scripts/create_mvp_test_user.py first.
EMAIL="${TEST_EMAIL:-mvp-e2e-test@mail.ru}"
PASS="${TEST_PASS:-}"
CREDS_FILE="${MVP_TEST_CREDS:-/root/.mvp_test_user_credentials}"
if [[ -z "${PASS}" && -f "${CREDS_FILE}" ]]; then
  PASS="$(grep '^password=' "${CREDS_FILE}" | cut -d= -f2-)"
fi

echo "=== HTTPS smoke ==="
curl -sk -o /dev/null -w "GET / → %{http_code} %{time_total}s\n" "${BASE_HTTPS}/"
curl -sk -o /dev/null -w "HTTP→HTTPS redirect → %{http_code}\n" -I "http://321997.fornex.cloud/" | head -1

if [[ -z "${PASS}" ]]; then
  echo "SKIP login metrics (set TEST_PASS)"
  exit 0
fi

echo "=== Login ==="
LOGIN_JSON=$(curl -sk -X POST "${API}/auth/login" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "username=${EMAIL}&password=${PASS}")
TOKEN=$(echo "$LOGIN_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)
if [[ -z "${TOKEN}" ]]; then
  echo "LOGIN FAILED: $LOGIN_JSON"
  exit 1
fi
echo "login ok, token len=${#TOKEN}"

echo "=== JWT /me ==="
curl -sk -o /dev/null -w "GET /auth/me → %{http_code} %{time_total}s\n" \
  -H "Authorization: Bearer ${TOKEN}" "${API}/auth/me"

echo "=== Reports cache (2x) ==="
curl -sk -o /dev/null -w "GET /reports #1 → %{time_total}s\n" \
  -H "Authorization: Bearer ${TOKEN}" "${API}/reports?limit=50"
curl -sk -o /dev/null -w "GET /reports #2 → %{time_total}s\n" \
  -H "Authorization: Bearer ${TOKEN}" "${API}/reports?limit=50"

MP=wildberries
START=2025-01-01
END=2025-12-31
echo "=== Dashboard summary ==="
curl -sk -o /dev/null -w "GET /dashboard/summary → %{time_total}s\n" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${API}/dashboard/summary?marketplace=${MP}&start=${START}&end=${END}"

echo "=== Forgot password ==="
curl -sk -w "POST /auth/forgot-password → %{http_code}\n" -o /tmp/forgot.json \
  -X POST "${API}/auth/forgot-password" -H 'Content-Type: application/json' \
  -d "{\"email\":\"${EMAIL}\"}"
cat /tmp/forgot.json; echo

echo "=== Rate limit burst login ==="
for i in $(seq 1 12); do
  code=$(curl -sk -o /dev/null -w "%{http_code}" -X POST "${API}/auth/login" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d 'username=rate.limit@test&password=wrong')
  echo "  attempt $i → $code"
  [[ "$code" == "429" ]] && echo "rate limit triggered on attempt $i" && break
done

echo "=== Old JWT (expect 401) ==="
curl -sk -w "old token /auth/me → %{http_code}\n" -o /dev/null \
  -H "Authorization: Bearer invalid.old.token" "${API}/auth/me"

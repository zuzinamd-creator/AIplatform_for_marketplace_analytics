#!/usr/bin/env bash
# Audit recovery/access artifacts and temporary password storage on VPS.
set -euo pipefail

echo "=== Security recovery / access file audit ==="
echo "timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

check_file() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    local mode owner size
    mode=$(stat -c '%a' "${path}")
    owner=$(stat -c '%U:%G' "${path}")
    size=$(stat -c '%s' "${path}")
    echo "FOUND  ${path}  mode=${mode} owner=${owner} size=${size}B"
    if [[ "${mode}" != "600" && "${mode}" != "400" ]]; then
      echo "  WARN: tighten to chmod 600"
    fi
  else
    echo "MISSING ${path}"
  fi
}

check_file /root/.mvp_test_user_credentials
check_file /root/.marketplace_smtp_credentials
check_file /root/AIplatform_for_marketplace_analytics/.env

echo ""
echo "--- Backup directory (may contain DB dumps with PII) ---"
BACKUP_DIR="${BACKUP_DIR:-/root/backups/marketplace-drill}"
if [[ -d "${BACKUP_DIR}" ]]; then
  ls -la "${BACKUP_DIR}" | tail -n +2
  echo "  owner: $(stat -c '%U:%G %a' "${BACKUP_DIR}")"
else
  echo "  (no backup dir)"
fi

echo ""
echo "--- Recommendations ---"
cat <<'EOF'
1. Store SMTP and E2E test passwords only in mode-600 files outside git:
   /root/.marketplace_smtp_credentials, /root/.mvp_test_user_credentials
2. Never commit .env; rotate Mail.ru app password after setup.
3. Delete obsolete zero-byte postgres-*.dump files from failed drills.
4. Restrict VPS SSH to operator IPs; disable password SSH auth.
5. After E2E tests, prefer --rotate on create_mvp_test_user.py over plaintext reuse.
6. Supabase Dashboard: limit team members with DB access; enable PITR backups.
EOF

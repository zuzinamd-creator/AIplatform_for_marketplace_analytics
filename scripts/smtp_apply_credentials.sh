#!/usr/bin/env bash
# Merge /root/.marketplace_smtp_credentials into .env (SMTP_* only). Never prints secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"
CREDS="${SMTP_CREDENTIALS_FILE:-/root/.marketplace_smtp_credentials}"

if [[ ! -f "${CREDS}" ]]; then
  echo "Missing ${CREDS}"
  echo "Create with: SMTP_USER=… SMTP_PASSWORD=… SMTP_FROM=…"
  exit 1
fi

# shellcheck disable=SC1090
source "${CREDS}"

for key in SMTP_USER SMTP_PASSWORD SMTP_FROM; do
  val="${!key:-}"
  if [[ -z "${val}" ]]; then
    echo "FAIL: ${key} empty in ${CREDS}"
    exit 1
  fi
done

python3 - <<'PY' "${ENV_FILE}" "${CREDS}"
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
creds_path = Path(sys.argv[2])
updates = {}
for line in creds_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k.startswith("SMTP_") or k == "APP_PUBLIC_URL":
        updates[k] = v

lines = env_path.read_text().splitlines() if env_path.exists() else []
out, seen = [], set()
for line in lines:
    if "=" in line and not line.startswith("#"):
        k = line.split("=", 1)[0]
        if k in updates:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
env_path.write_text("\n".join(out) + "\n")
print(f"Updated {env_path} ({len(updates)} keys from {creds_path})")
PY

echo "Restart backend: systemctl restart marketplace-backend"

#!/usr/bin/env bash
# Create marketplace_app role, FORCE RLS migration, switch runtime DATABASE_URL.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${ROOT}/.env"
CREDS="${MARKETPLACE_DB_CREDS:-/root/.marketplace_db_credentials}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}"
  exit 1
fi

# shellcheck disable=SC1090
# Do not source full .env (values may contain spaces); read DATABASE_URL only.
DATABASE_URL="$(python3 - <<'PY' "${ENV_FILE}"
import sys
from pathlib import Path
for line in Path(sys.argv[1]).read_text().splitlines():
    if line.startswith("DATABASE_URL="):
        print(line.split("=", 1)[1])
        break
PY
)"

gen_password() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
}

if [[ -f "${CREDS}" ]] && grep -q '^MARKETPLACE_APP_DB_PASSWORD=' "${CREDS}"; then
  # shellcheck disable=SC1090
  source "${CREDS}"
else
  MARKETPLACE_APP_DB_PASSWORD="$(gen_password)"
  umask 077
  {
    echo "# Marketplace runtime DB role (mode 600). Never commit."
    echo "MARKETPLACE_APP_DB_PASSWORD=${MARKETPLACE_APP_DB_PASSWORD}"
  } > "${CREDS}"
  chmod 600 "${CREDS}"
fi

# Preserve postgres URL for Alembic / maintenance.
if ! grep -q '^ALEMBIC_DATABASE_URL=' "${ENV_FILE}"; then
  python3 - <<PY "${ENV_FILE}" "${DATABASE_URL}"
import sys
from pathlib import Path
env_path = Path(sys.argv[1])
postgres_url = sys.argv[2]
lines = env_path.read_text().splitlines()
out = []
inserted = False
for line in lines:
    out.append(line)
    if line.startswith("DATABASE_URL=") and not inserted:
        out.append(f"ALEMBIC_DATABASE_URL={postgres_url}")
        inserted = True
env_path.write_text("\n".join(out) + "\n")
print(f"Saved ALEMBIC_DATABASE_URL in {env_path}")
PY
fi

export MARKETPLACE_APP_DB_PASSWORD
cd "${ROOT}"
PYTHONPATH=. .venv/bin/alembic upgrade head

python3 - <<PY "${ENV_FILE}" "${CREDS}"
import sys
from pathlib import Path
from urllib.parse import quote
env_path = Path(sys.argv[1])
creds = {}
for line in Path(sys.argv[2]).read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        creds[k] = v
password = creds["MARKETPLACE_APP_DB_PASSWORD"]
# Replace user in DATABASE_URL, keep host/db/ssl params
lines = env_path.read_text().splitlines()
out = []
for line in lines:
    if line.startswith("DATABASE_URL="):
        raw = line.split("=", 1)[1]
        if raw.startswith("postgresql"):
            # postgresql+asyncpg://user:pass@host:port/db?...
            prefix, rest = raw.split("://", 1)
            _, tail = rest.split("@", 1)
            safe = quote(password, safe="")
            out.append(f"DATABASE_URL={prefix}://marketplace_app:{safe}@{tail}")
            continue
    out.append(line)
env_path.write_text("\n".join(out) + "\n")
print("Updated DATABASE_URL to marketplace_app")
PY

echo "Restart: systemctl restart marketplace-backend marketplace-worker"
echo "Credentials: ${CREDS}"

#!/usr/bin/env bash
# Disaster recovery drill: measure backup export + document restore steps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${BACKUP_DIR:-/root/backups/marketplace-drill}"
mkdir -p "${BACKUP_DIR}"

echo "=== DR drill ${STAMP} ==="

# 1) App config snapshot (no secrets dump)
echo "--- Config snapshot ---"
tar -czf "${BACKUP_DIR}/app-config-${STAMP}.tar.gz" \
  -C "${ROOT}" \
  .env.example \
  deploy/nginx \
  alembic/versions \
  scripts/deploy-frontend.sh \
  2>/dev/null || true
ls -lh "${BACKUP_DIR}/app-config-${STAMP}.tar.gz"

# 2) Frontend static
echo "--- Frontend static ---"
tar -czf "${BACKUP_DIR}/frontend-static-${STAMP}.tar.gz" -C /var/www marketplace-analytics
ls -lh "${BACKUP_DIR}/frontend-static-${STAMP}.tar.gz"

# 3) PostgreSQL logical export (schema+data for drill; Supabase is source of truth)
echo "--- PostgreSQL pg_dump ---"
DB_URL="$(grep '^DATABASE_URL=' "${ROOT}/.env" | cut -d= -f2- | sed -E 's/postgresql\+asyncpg/postgresql/; s/\?.*$//')"
PG_DUMP_BIN="${PG_DUMP_BIN:-pg_dump}"
if command -v "${PG_DUMP_BIN}" >/dev/null 2>&1; then
  echo "pg_dump binary: $(command -v "${PG_DUMP_BIN}") ($(${PG_DUMP_BIN} --version))"
  START=$(date +%s)
  if PGSSLMODE=require "${PG_DUMP_BIN}" "${DB_URL}" --format=custom --no-owner --file "${BACKUP_DIR}/postgres-${STAMP}.dump" 2>"${BACKUP_DIR}/pg_dump.err"; then
    END=$(date +%s)
    ls -lh "${BACKUP_DIR}/postgres-${STAMP}.dump"
    echo "pg_dump elapsed: $((END-START))s"
    if command -v pg_restore >/dev/null 2>&1; then
      echo "--- pg_restore --list (integrity check) ---"
      LIST_FILE="${BACKUP_DIR}/pg_restore-list-${STAMP}.txt"
      pg_restore --list "${BACKUP_DIR}/postgres-${STAMP}.dump" > "${LIST_FILE}"
      head -5 "${LIST_FILE}"
      echo "... ($(wc -l < "${LIST_FILE}") objects)"
      RESTORE_START=$(date +%s)
      # Logical restore drill into disposable docker postgres if available
      if command -v docker >/dev/null 2>&1; then
        DRILL_DB="marketplace_drill_${STAMP}"
        docker rm -f "${DRILL_DB}" >/dev/null 2>&1 || true
        docker run -d --name "${DRILL_DB}" -e POSTGRES_PASSWORD=drill -p 5544:5432 postgres:17-alpine >/dev/null
        for i in $(seq 1 30); do docker exec "${DRILL_DB}" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
        PGPASSWORD=drill pg_restore -h 127.0.0.1 -p 5544 -U postgres -d postgres --no-owner --role=postgres "${BACKUP_DIR}/postgres-${STAMP}.dump" 2>"${BACKUP_DIR}/pg_restore.err" || true
        RESTORE_END=$(date +%s)
        ROWS=$(PGPASSWORD=drill psql -h 127.0.0.1 -p 5544 -U postgres -d postgres -tAc "select count(*) from users" 2>/dev/null || echo "n/a")
        echo "docker restore users.count=${ROWS} elapsed=$((RESTORE_END-RESTORE_START))s"
        docker rm -f "${DRILL_DB}" >/dev/null 2>&1 || true
      else
        echo "docker not available — restore drill skipped (dump list validated)"
      fi
    fi
  else
    echo "pg_dump failed (common: client/server version mismatch on Supabase PG17):"
    cat "${BACKUP_DIR}/pg_dump.err"
    echo "Use Supabase Dashboard → Database → Backups (daily snapshots on paid plans)"
  fi
else
  echo "pg_dump not installed — use Supabase Dashboard → Database → Backups"
fi

echo "--- DB inventory (async export baseline) ---"
PYTHONPATH="${ROOT}" "${ROOT}/.venv/bin/python3" - <<'PY'
import asyncio, os, time
from pathlib import Path
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k,v=line.split("=",1); os.environ.setdefault(k,v)
from sqlalchemy import text
from app.core.database import SessionLocal
async def main():
    t0=time.time()
    async with SessionLocal() as db:
        tables=["users","reports","etl_jobs","financial_ledger_entries","cost_history"]
        for t in tables:
            n=(await db.execute(text(f"select count(*) from {t}"))).scalar()
            print(f"  {t}: {n}")
    print(f"  inventory query elapsed: {time.time()-t0:.1f}s")
asyncio.run(main())
PY

echo ""
echo "Restore outline (new VPS):"
echo "  1. Provision Ubuntu VPS, install nginx/python3.12"
echo "  2. Clone repo, restore .env from secure store"
echo "  3. alembic upgrade head (or pg_restore into fresh Supabase)"
echo "  4. systemctl enable marketplace-backend marketplace-worker"
echo "  5. rsync frontend-static tarball → /var/www/marketplace-analytics"
echo "  6. deploy nginx config from deploy/nginx/"
echo "  7. Verify /health/ready and login"

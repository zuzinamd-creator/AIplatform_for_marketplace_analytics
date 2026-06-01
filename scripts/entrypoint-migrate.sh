#!/usr/bin/env bash
set -euo pipefail

MIGRATION_LOCK_KEY="${MIGRATION_LOCK_KEY:-83472931}"

if command -v pg_isready >/dev/null 2>&1; then
  /app/scripts/wait-for-postgres.sh
fi

if command -v psql >/dev/null 2>&1 && [[ -n "${DATABASE_URL:-}" ]]; then
  echo "Acquiring migration advisory lock (${MIGRATION_LOCK_KEY})..."
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "SELECT pg_advisory_lock(${MIGRATION_LOCK_KEY});"
  trap 'psql "${DATABASE_URL}" -c "SELECT pg_advisory_unlock(${MIGRATION_LOCK_KEY});"' EXIT
fi

echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete"

exec "$@"

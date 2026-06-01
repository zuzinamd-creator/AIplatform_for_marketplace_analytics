#!/usr/bin/env bash
set -euo pipefail

host="${POSTGRES_HOST:-postgres}"
port="${POSTGRES_PORT:-5432}"
user="${POSTGRES_USER:-postgres}"
db="${POSTGRES_DB:-marketplace}"
max_attempts="${WAIT_MAX_ATTEMPTS:-60}"
sleep_seconds="${WAIT_SLEEP_SECONDS:-2}"

attempt=1
until pg_isready -h "$host" -p "$port" -U "$user" -d "$db" >/dev/null 2>&1; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "PostgreSQL is not ready after ${max_attempts} attempts"
    exit 1
  fi
  echo "Waiting for PostgreSQL (${attempt}/${max_attempts})..."
  attempt=$((attempt + 1))
  sleep "$sleep_seconds"
done

echo "PostgreSQL is ready"

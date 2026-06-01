#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
docker compose down -v
docker compose up -d postgres
docker compose run --rm migrate
docker compose up -d api worker orchestrator nginx
echo "Database reset complete."

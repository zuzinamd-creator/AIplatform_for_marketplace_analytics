#!/usr/bin/env bash
# Start Uptime Kuma on localhost:3001 (no docker compose plugin required).
set -euo pipefail

NAME="marketplace-uptime-kuma"
VOLUME="marketplace_uptime_kuma_data"

if docker ps -a --format '{{.Names}}' | grep -qx "${NAME}"; then
  docker start "${NAME}" 2>/dev/null || true
else
  docker run -d \
    --name "${NAME}" \
    --restart unless-stopped \
    -p 127.0.0.1:3001:3001 \
    -v "${VOLUME}:/app/data" \
    louislam/uptime-kuma:1
fi

echo "Uptime Kuma: http://127.0.0.1:3001"
docker ps --filter "name=${NAME}" --format '{{.Names}} {{.Status}}'

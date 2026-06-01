#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — set AI_OPENAI_API_KEY and SECRET_KEY."
fi

docker compose up -d --build

echo "Waiting for http://localhost:8080/health ..."
for _ in $(seq 1 40); do
  if curl -fsS "http://localhost:8080/health" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

echo "Backend: http://localhost:8080"
echo "Frontend: cd frontend && cp -n .env.local.example .env.local && npm install && npm run dev"
echo "Smoke: python scripts/local/run-local-smoke-test.py"

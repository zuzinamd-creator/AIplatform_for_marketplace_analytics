#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — set AI_OPENAI_API_KEY and SECRET_KEY."
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed on this machine."
  echo "Use the no-Docker dev script instead:"
  echo "  bash scripts/local/start-dev-no-docker.sh"
  echo ""
  echo "Or install Docker, then re-run this script:"
  echo "  sudo apt update && sudo apt install -y docker.io docker-compose-v2"
  echo "  sudo usermod -aG docker \"\$USER\"   # log out/in after this"
  exit 1
fi

docker compose up -d --build

echo "Waiting for http://localhost:8080/health ..."
for _ in $(seq 1 40); do
  if curl -fsS "http://localhost:8080/health" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

echo "Seller UI:  http://localhost:8080/app/dashboard  (nginx → Vite; also http://localhost:5173)"
echo "API:        http://localhost:8080/api/v1"
echo "If UI looks stale: docker compose restart frontend"
echo "Smoke: python scripts/local/run-local-smoke-test.py"

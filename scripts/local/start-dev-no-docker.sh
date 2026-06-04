#!/usr/bin/env bash
# Local stack without Docker: API (uvicorn :8000) + seller UI (Vite :5173).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — set DATABASE_URL and SECRET_KEY."
fi

if [[ ! -x .venv/bin/python ]]; then
  echo "Creating Python venv..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements-dev.txt
fi

# Frontend must call the API directly (no nginx on :8080 without Docker).
ENV_LOCAL="$ROOT/frontend/.env.local"
if [[ ! -f "$ENV_LOCAL" ]] || ! grep -q '^VITE_API_BASE_URL=http://localhost:8000' "$ENV_LOCAL" 2>/dev/null; then
  cat > "$ENV_LOCAL" <<'EOF'
VITE_API_BASE_URL=http://localhost:8000
VITE_API_PREFIX=/api/v1
EOF
  echo "Wrote frontend/.env.local (API → http://localhost:8000)"
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT/frontend" && npm install)
fi

API_PID=""
FRONT_PID=""
cleanup() {
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$FRONT_PID" ]] && kill "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API on http://127.0.0.1:8000 ..."
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "Waiting for API health..."
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Starting frontend on http://127.0.0.1:5173 ..."
(cd "$ROOT/frontend" && npm run dev -- --host 0.0.0.0 --port 5173) &
FRONT_PID=$!

sleep 2
echo ""
echo "Seller UI:  http://127.0.0.1:5173/app/dashboard"
echo "API:        http://127.0.0.1:8000/api/v1"
echo "Health:     http://127.0.0.1:8000/health"
echo ""
echo "Press Ctrl+C to stop both processes."
wait

# Start full local stack (Docker: postgres, migrate, api, worker, orchestrator, nginx)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — edit AI_OPENAI_API_KEY and SECRET_KEY before real AI testing."
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is not installed."
    Write-Host "On Linux/macOS without Docker, run:"
    Write-Host "  bash scripts/local/start-dev-no-docker.sh"
    Write-Host ""
    Write-Host "Or install Docker Desktop / docker.io, then re-run this script."
    exit 1
}

Write-Host "Building and starting Docker services..."
docker compose up -d --build

Write-Host ""
Write-Host "Waiting for API health..."
$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8080/health" -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { break }
    } catch { Start-Sleep -Seconds 3 }
}
else {
    Write-Warning "API not healthy yet — check: docker compose logs api"
}

Write-Host ""
Write-Host "Seller UI (via nginx): http://localhost:8080/app/dashboard"
Write-Host "Seller UI (direct):    http://localhost:5173/app/dashboard"
Write-Host "Health:                http://localhost:8080/health"
Write-Host "API prefix:            http://localhost:8080/api/v1"
Write-Host ""
Write-Host "Frontend runs in Docker (service: frontend). If UI looks stale:"
Write-Host "  docker compose restart frontend"
Write-Host ""
Write-Host "Smoke test: .venv\Scripts\python.exe scripts\local\run-local-smoke-test.py"

# Start full local stack (Docker: postgres, migrate, api, worker, orchestrator, nginx)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — edit AI_OPENAI_API_KEY and SECRET_KEY before real AI testing."
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
Write-Host "Backend (via nginx): http://localhost:8080"
Write-Host "Health:            http://localhost:8080/health"
Write-Host "API prefix:        http://localhost:8080/api/v1"
Write-Host ""
Write-Host "Start frontend in another terminal:"
Write-Host "  cd frontend"
Write-Host "  copy .env.local.example .env.local"
Write-Host "  npm install"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Smoke test: .venv\Scripts\python.exe scripts\local\run-local-smoke-test.py"

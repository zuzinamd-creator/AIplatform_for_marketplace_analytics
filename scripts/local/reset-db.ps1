# Reset local Postgres + uploads volumes and re-run migrations
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root

Write-Host "Stopping stack and removing volumes..."
docker compose down -v

Write-Host "Starting postgres + migrate..."
docker compose up -d postgres
docker compose run --rm migrate

Write-Host "Starting application services..."
docker compose up -d api worker orchestrator nginx

Write-Host "Done. Fresh database. Re-register users in the UI."

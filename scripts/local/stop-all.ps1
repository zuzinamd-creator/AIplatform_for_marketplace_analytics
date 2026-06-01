# Stop Docker stack (keeps volumes)
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $Root
docker compose down
Write-Host "Stopped. Data volumes preserved. Use reset-db.ps1 to wipe Postgres/uploads."

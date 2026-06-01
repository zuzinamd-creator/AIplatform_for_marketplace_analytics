Set-Location (Split-Path $PSScriptRoot -Parent)
docker compose -p ma_integration -f docker-compose.integration.yml --env-file .env.integration up -d --build


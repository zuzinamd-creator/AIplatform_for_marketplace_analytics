Set-Location (Split-Path $PSScriptRoot -Parent)
$env:RUN_INTEGRATION_TESTS="true"
if (-not $env:TEST_DATABASE_URL) {
  $env:TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test"
}
if (Test-Path .\.venv\Scripts\python.exe) {
  .\.venv\Scripts\python -m pytest tests\integration -m integration
} else {
  python -m pytest tests\integration -m integration
}


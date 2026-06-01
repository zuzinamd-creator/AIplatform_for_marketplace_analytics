.PHONY: integration-up integration-test integration-reset

integration-up:
	docker compose -p ma_integration -f docker-compose.integration.yml --env-file .env.integration up -d --build

integration-test:
	RUN_INTEGRATION_TESTS=true TEST_DATABASE_URL=$$(python -c "import os; print(os.getenv('TEST_DATABASE_URL','postgresql+asyncpg://postgres:postgres@localhost:5434/marketplace_test'))") \
	python -m pytest tests/integration -m integration

integration-reset:
	docker compose -p ma_integration -f docker-compose.integration.yml --env-file .env.integration down -v


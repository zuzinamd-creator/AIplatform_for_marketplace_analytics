# Environment Variables

Reference for deployment and local development. Canonical template: `.env.example` in repository root.

Archived full list from pre-v0.6 README: [docs/archive/README_pre_v06.md](../archive/README_pre_v06.md) (§19).

---

## Core

| Variable | Description |
|----------|-------------|
| `ENVIRONMENT_MODE` | `MAIN` (Supabase production-like), `LOCAL_DEV`, or `INTEGRATION` |
| `DATABASE_URL` | PostgreSQL URL (`postgresql+asyncpg://…`) |
| `SECRET_KEY` | JWT signing key (≥ 32 random chars) |
| `ALGORITHM` | JWT algorithm (default `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT TTL |
| `LOG_LEVEL` | JSON log level (`INFO`, `DEBUG`, …) |
| `DEBUG` | FastAPI debug mode |
| `MAINTENANCE_MODE` | Kill switch for non-health endpoints |

---

## Storage

| Variable | Description |
|----------|-------------|
| `STORAGE_BACKEND` | `supabase` or `local` |
| `ALLOW_LOCAL_STORAGE_FALLBACK` | Allow local uploads in dev (`true`/`false`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Service role or anon key |
| `SUPABASE_STORAGE_BUCKET` | Reports bucket name (default `reports`) |
| `UPLOADS_DIR` | Local uploads path (Docker: `/app/uploads`) |

---

## Migrations

| Variable | Description |
|----------|-------------|
| `ALEMBIC_BYPASS_RLS` | System session for migrations |
| `ALEMBIC_DATABASE_URL` | Owner role URL (optional, separate from app role) |
| `MIGRATION_LOCK_KEY` | Advisory lock for migrations |

---

## ETL worker / queue

| Variable | Description |
|----------|-------------|
| `WORKER_HEARTBEAT_INTERVAL_SECONDS` | Heartbeat interval (default 15) |
| `JOB_MAX_ATTEMPTS` | Queue retry limit |
| `JOB_VISIBILITY_TIMEOUT_SECONDS` | Claim/heartbeat timeout |
| `JOB_RETRY_BASE_DELAY_SECONDS` | Exponential backoff base (default 30) |
| `ETL_AGGREGATE_LOCK_TIMEOUT_MS` | Phase 3 lock timeout (default 5000) |

---

## Orchestrator

| Variable | Description |
|----------|-------------|
| `ORCHESTRATOR_ENABLED` | Enable rebuild dispatcher |
| `ORCHESTRATOR_POLL_INTERVAL_SECONDS` | Poll interval |
| `ORCHESTRATOR_MAX_DISPATCH_PER_CYCLE` | Max dispatches per cycle |

See [docs/runtime/runtime_architecture.md](../runtime/runtime_architecture.md) for runtime automation details.

---

## AI

| Variable | Description |
|----------|-------------|
| `AI_ENABLED` | Master switch for AI runs |
| `AI_PROVIDER` | `mock` (default) or `openai` / `openai_compatible` |
| `AI_OPENAI_API_KEY` | External LLM API key |
| `AI_OPENAI_BASE_URL` | Custom OpenAI-compatible base URL |
| `AI_OPENAI_MODEL` | Model name (default `gpt-4o-mini`) |
| `AI_PROMPT_RUNTIME_VERSION` | Prompt runtime version (default `v3`) |
| `AI_PROVIDER_MAX_RETRIES` | Bounded provider retries |
| `AI_RATE_LIMIT_PER_MINUTE` | Per-tenant run rate limit (0 = off) |
| `AI_MEMORY_MAX_TURNS` | Max `ai_session_turns` per session |
| `AI_DISABLED_AGENTS` | Comma-separated agent kill switch |
| `AI_EXECUTION_TIMEOUT_SECONDS` | Max wall time per AI run |
| `AI_STALE_REBUILD_PENDING_WARN` | Degraded context when rebuild backlog exceeds threshold |

---

## SMTP (password reset)

| Variable | Description |
|----------|-------------|
| `SMTP_HOST` | SMTP server |
| `SMTP_PORT` | SMTP port |
| `SMTP_USER` / `SMTP_PASSWORD` | Credentials |
| `SMTP_FROM` | From address |
| `SMTP_USE_TLS` | TLS enabled |
| `APP_PUBLIC_URL` | Public URL for reset links |

---

## Integration testing

| Variable | Description |
|----------|-------------|
| `TEST_DATABASE_URL` | Separate test DB (port 5434 typical) |

See [docs/testing/local_runtime_testing.md](../testing/local_runtime_testing.md).

# Local Runtime Testing

Manual testing guide for running the full marketplace analytics platform locally with **real seller workflows** and optional **real OpenAI-compatible LLM** calls.

Governance guarantees (RLS, advisory-only AI, governed KPIs, no ledger mutation by AI) remain unchanged in local mode.

---

## Expected local architecture

```
Browser (Vite :5173)
    → API via nginx (:8080) or direct uvicorn (:8000)
        → FastAPI (api)
        → PostgreSQL (:5432)
    ← ETL worker (processes uploads / queue)
    ← Orchestrator (rebuild dispatch)
```

| Component | Role |
|-----------|------|
| `postgres` | Primary database |
| `migrate` | Alembic `upgrade head` (one-shot) |
| `api` | REST + SSE AI streaming |
| `worker` | Report ETL + job queue |
| `orchestrator` | Rebuild / runtime dispatch |
| `nginx` | Reverse proxy `:8080` → api |

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Python 3.12+ venv at repo root (`.venv`)
- Node 20+ for frontend
- Wildberries `.xlsx` report for upload tests (place under `tests/*.xlsx` or use your own export)

---

## 1. Environment setup

```powershell
cd <repo-root>
copy .env.example .env
```

Edit `.env` for local real testing:

| Variable | Local recommendation |
|----------|---------------------|
| `SECRET_KEY` | Long random string (not `change-me`) |
| `DATABASE_URL` | Leave default for Docker; use `postgresql://postgres:postgres@localhost:5432/marketplace` for hybrid host API |
| `STORAGE_BACKEND` | `local` or `supabase` + `ALLOW_LOCAL_STORAGE_FALLBACK=true` |
| `AI_PROVIDER` | `openai`, `openrouter`, or `deepseek` (not `mock` for real LLM) |
| `AI_OPENAI_API_KEY` | Your API key |
| `AI_OPENAI_MODEL` | e.g. `gpt-4o-mini` |
| `AI_PROMPT_RUNTIME_VERSION` | `v3` |
| `AI_ENABLE_STREAMING` | `true` |

See also `docs/ai/provider_setup.md`.

---

## 2. Startup sequence

### Option A — Full stack (recommended)

```powershell
.\scripts\local\start-all.ps1
```

Or (Git Bash / WSL):

```bash
bash scripts/local/start-all.sh
```

Equivalent manual steps:

```bash
docker compose up -d --build
```

Wait until:

- `curl http://localhost:8080/health` → `{"status":"ok"}`
- `curl http://localhost:8080/health/ready` → `{"status":"ready"}`

### Frontend (second terminal)

```powershell
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:5173** (Vite). API calls go to `http://localhost:8080` per `.env.local`.

### Option B — Hybrid (Postgres in Docker, API on host)

```bash
docker compose up -d postgres
docker compose run --rm migrate
```

In `.env` on host:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/marketplace
UPLOADS_DIR=uploads
```

```powershell
.venv\Scripts\activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
python -m app.etl.worker
python -m app.runtime.orchestration_worker
```

Point frontend at `VITE_API_BASE_URL=http://localhost:8000` or run nginx separately.

---

## 3. URLs

| URL | Purpose |
|-----|---------|
| http://localhost:8080/health | Liveness (no auth) |
| http://localhost:8080/health/ready | DB readiness (no auth) |
| http://localhost:8080/api/v1 | API prefix |
| http://localhost:5173 | Frontend (Vite dev) |
| http://localhost:5173/app/dashboard | Seller dashboard |
| http://localhost:5173/app/ai/today | Today's Focus |
| http://localhost:5173/app/ai/recommendations | AI inbox |
| http://localhost:5173/app/reports/upload | Report upload |

Authenticated ops (JWT required):

- `GET /api/v1/ops/runtime/health`
- `GET /api/v1/ai/providers/status`
- `GET /api/v1/ai/usage`

---

## 4. Smoke verification

```powershell
.venv\Scripts\python.exe scripts\local\run-local-smoke-test.py
```

Environment:

- `SMOKE_BASE_URL` — default `http://localhost:8080`
- `SMOKE_SKIP_AI_PROBE=1` — skip live LLM ping (faster, no API cost)

Checks: `/health`, `/health/ready`, register/login, ops runtime health, AI provider status, optional LLM probe.

---

## 5. Login flow

1. Open http://localhost:5173/register
2. Register seller account (password ≥ 8 chars)
3. Login → redirected to `/app/onboarding` or dashboard
4. Token stored in `localStorage` (`ma.accessToken`)

If `SECRET_KEY` was changed after registration, existing tokens invalidate — re-login.

---

## 6. Upload flow

1. `/app/reports/upload` — drag Wildberries weekly `.xlsx`
2. Expect: upload accepted → report row → ETL job `pending` / `running`
3. Worker must be running (`docker compose` includes `worker`)
4. `/app/reports` — status progresses to processed
5. Storage: with `STORAGE_BACKEND=local` or fallback, files land in Docker volume `uploads_data` or host `uploads/`

**Duplicate checksum:** second upload of same file should not duplicate ledger rows.

---

## 7. AI workflow

1. Ensure report processed and KPIs available on dashboard
2. `/app/ai/recommendations` — run intelligence (or use “Run stream” for SSE demo)
3. Open recommendation detail — explainability, seller usefulness fields, ask follow-up
4. `/app/ai/today` — Today's Focus briefing
5. `/app/ai/usage` — token/cost summary
6. Workflow actions: save / snooze / dismiss / complete

**Real LLM checklist:**

- `GET /api/v1/ai/providers/status` → `primary_provider` ≠ `mock`
- `prompt_runtime_version` = `v3`
- Run intelligence → `ai_execution_runs` row with non-mock `runtime_metadata` (when implemented in run detail)
- Streaming: inbox “Run stream” or `POST /api/v1/ai/runs/stream` (SSE)

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `connection refused` on :8080 | Stack not up | `docker compose ps`, `start-all.ps1` |
| `/health/ready` fails | Postgres not ready / wrong URL | `docker compose logs postgres`, check `DATABASE_URL` in api container |
| Migrations not applied | `migrate` service failed | `docker compose logs migrate`, `docker compose run --rm migrate` |
| Upload stuck `pending` | Worker down | `docker compose up -d worker`, check logs |
| AI always mock | `AI_PROVIDER=mock` or missing key | Set `AI_PROVIDER=openai` + `AI_OPENAI_API_KEY` in `.env`, restart `api` |
| 401 on API calls | Expired/missing JWT | Re-login |
| CORS errors from Vite | Wrong API base | `frontend/.env.local` → `VITE_API_BASE_URL=http://localhost:8080` |
| Port 5432 in use | Other Postgres | Change compose port mapping or stop other instance |
| `SECRET_KEY must be set` | Default secret in prod-like check | Set non-default `SECRET_KEY` in `.env` |

View logs:

```bash
docker compose logs -f api worker orchestrator
```

Reset database (destructive):

```powershell
.\scripts\local\reset-db.ps1
```

Stop stack:

```powershell
.\scripts\local\stop-all.ps1
```

---

## 9. Expected states

| Stage | Report status | Queue | Dashboard |
|-------|---------------|-------|-----------|
| After upload | `uploaded` / processing | job pending | may show queue activity |
| ETL success | `processed` | job completed | KPIs populated |
| Stale rebuild | freshness warning | rebuild pending | degraded badges |
| AI run complete | — | — | recommendations in inbox |

---

## 10. Common runtime failures

- **Worker OOM on large xlsx** — reduce file size or increase Docker memory for `worker`
- **Cost cap block** — `AI_MAX_COST_PER_DAY_USD` exceeded; check `/app/ai/usage`
- **Circuit breaker open** — repeated provider failures → mock degradation; wait or fix API key
- **RLS empty results** — wrong user token / cross-tenant ID in manual API calls

---

## 11. Manual QA checklist (minimal)

Use this for a single end-to-end seller session:

- [ ] Register + login
- [ ] Upload WB weekly report (real file)
- [ ] Report reaches `processed`; worker log shows no fatal error
- [ ] Dashboard KPIs match order of magnitude (not empty)
- [ ] Run AI intelligence → recommendation appears in inbox
- [ ] Recommendation has: why, action, impact ranges, priority tier
- [ ] Today's Focus lists the item or explains empty state
- [ ] Complete or dismiss workflow → usefulness metrics update
- [ ] Stale/degraded banner visible when rebuild pending (optional: trigger rebuild)
- [ ] `providers/status` shows real provider when key configured
- [ ] SSE stream produces tokens (inbox stream button)
- [ ] `/app/ai/usage` shows run after intelligence

---

## 12. Real AI testing notes

- AI is **advisory only** — never changes marketplace listings or ledger directly
- Prompt **v3** uses structured JSON contracts; invalid JSON falls back to validation errors
- Mock provider is valid for UI testing without API cost
- For OpenAI: `AI_PROVIDER=openai`, key in `AI_OPENAI_API_KEY`
- For OpenRouter: `AI_PROVIDER=openrouter`, `AI_OPENAI_BASE_URL=https://openrouter.ai/api/v1`, model e.g. `openai/gpt-4o-mini`

---

## Related docs

- `README.md` §34 Local Runtime Testing
- `docs/ai/provider_setup.md`
- `docs/product/ai_assistant_workflows.md`
- `docs/frontend/user_workflows.md`

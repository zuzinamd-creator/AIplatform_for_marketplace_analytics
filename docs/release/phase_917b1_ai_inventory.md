# Phase 9.17-B1 — Full AI inventory

**Date:** 2026-07-19  
**Scope:** Complete inventory of AI usage; Auto-AI after report remains **off** by default.  
**ETL optimization:** out of scope.

---

## 1. Entry-point table (production-relevant)

| Компонент | Файл | Назначение | Как запускается | LLM tokens? |
|-----------|------|------------|-----------------|-------------|
| Worker / ETL hook | `app/etl/worker.py` → `app/etl/post_report_ai.py` | Optional post-ACK `revenue_insight` | **Automatic** after finance ETL — **disabled by default** (`AI_AUTO_RECOMMEND_AFTER_REPORT=false`) | Only if auto flag true |
| Recommendations UI | `frontend/.../RecommendationsPage.tsx` | «Запустить анализ» → period intelligence | **Manual** (button) | Yes (if provider ≠ mock) |
| Onboarding | `frontend/.../OnboardingPage.tsx` | «Запустить ИИ-анализ» | **Manual** (button) | Yes |
| AI API — intelligence | `app/api/ai.py` `POST /intelligence/runs`, `/intelligence/period-runs` | Full Period Intelligence | **Manual** (HTTP) | Yes |
| AI API — legacy runs | `app/api/ai.py` `POST /runs`, `/runs/stream` | `AIAnalyticsEngine` only (insight, may skip full decision layer) | **Manual** (HTTP; FE stream path on Recommendations) | Yes |
| Dashboard summary | `app/services/dashboard_service.py` | Embeds AI ops / today’s focus / last 5 recs | **Automatic on page load** | **No** — DB read of existing rows |
| Digest / Today / Ask | `app/api/ai.py` digests, todays-focus, ask | Product surfaces over stored recommendations | **Manual** (page/API) | **No** — deterministic over DB |
| Feedback / workflow | `app/api/ai.py` feedback, workflow patch | Seller accept/dismiss/snooze | **Manual** | No |
| Status / costs / usage | `app/api/ai.py` operational, costs, providers, usage | Observability | **Manual** | No |
| Business Signals / Insight Engine V1 | `frontend/.../chart-insights.ts` + dashboard FE | Captions / alerts | Deterministic FE | **No AI** |
| KPIs / charts / FS / Top SKU | `AnalyticsService` + FE | Core analytics | ETL aggregates | **No AI** |
| Orchestrator schedules | `app/runtime/scheduling/*` | Rebuild / health / queue | Automatic rebuild ops | **No AI** |
| API lifespan | `app/main.py` | Startup validation only | Startup | **No AI run** |
| Operating Director | `app/ai/director/*` | Scaffold / strangler candidate | **Not wired** to production path | Unused |
| Ops scripts | `scripts/backfill_ai_recommendations.py`, audits, replay | Offline / ops | **Manual CLI** | Yes if run with real provider |

---

## 2. Process map

### A. Used by the seller / operator directly (manual)

| Process | Path | Tokens |
|---------|------|--------|
| Period Intelligence («Запустить анализ») | FE → `run_intelligence_for_period` → `AIIntelligenceEngine` → `AIAnalyticsEngine` + `MultiAgentCoordinator` | Yes |
| Onboarding first AI | FE → `run_intelligence` (`inventory_insight`) | Yes |
| Legacy/stream run | FE `POST /ai/runs/stream` | Yes |
| List / detail recommendations | GET recommendations | No |
| Ask follow-up | Deterministic `answer_follow_up` | No |
| Digests / Today’s focus | Aggregate existing `AIRecommendation` | No |
| Workflow + feedback | PATCH/POST | No |

### B. Automatic (must stay empty for product rule)

| Process | Status after 9.17-B/B1 |
|---------|------------------------|
| Post-ETL `maybe_generate_recommendation_after_report` | **OFF by default** — logs `post_report_ai_skipped_disabled` |
| Cron / timer for AI | **None** (`marketplace-dr-drill.timer` is DR, not AI) |
| Orchestrator schedules | Rebuild/health only — **no AI** |
| Webhook → AI | **None found** |
| Startup → AI run | **None** (validation only) |

Dashboard auto-loads AI **read APIs** (focus/recs/ops). That is **not** an intelligence run and does **not** create recommendations or spend LLM tokens.

### C. Present in code but unused / legacy

| Item | Notes | Recommendation |
|------|-------|----------------|
| `OperatingDirectorPipeline` | Scaffold; not called from `AIIntelligenceEngine` | Keep scaffold; do not enable without product decision |
| Workflows rarely used in FE | `anomaly_explanation`, `trend_explanation`, `causal_analysis`, `recommendation`, `risk_detection`, `forecast_prep` | API-capable; FE primary = `revenue_insight` (+ onboarding `inventory_insight`) |
| `scripts/backfill_ai_recommendations.py` | Manual backfill | Ops-only; do not cron |
| Archive docs describing auto-AI=true | Historical | Superseded by `ai_trigger_policy.md` |

---

## 3. Hidden auto-trigger checklist

| Mechanism | Path | Conditions | Production? |
|-----------|------|------------|-------------|
| Worker post-ACK hook | `worker.py` → `post_report_ai.py` | Finance report + `AI_ENABLED` + `AI_AUTO_RECOMMEND_AFTER_REPORT` | Hook **called**; auto path **skipped** when flag false |
| systemd timers | `marketplace-dr-drill.timer`, frontend cleanup | DR / cleanup | No AI |
| Orchestrator | `ScheduleKind.*` | Rebuild/health | No AI |
| FastAPI lifespan | `app/main.py` | Env validation | No AI |
| Dashboard gather | `dashboard_service` | Every summary request | Read-only AI tables |

---

## 4. Policy confirmation (9.17-B / B1)

| Check | Result |
|-------|--------|
| Auto AI after upload | **Disabled** (default `False` + `.env` `false`) |
| Dashboard KPIs | Via `AnalyticsService` — **independent of AI** |
| Charts / FS / Top SKU / Business Signals | Deterministic analytics / FE — **independent of AI** |
| Insight Engine V1 | FE-only — **no LLM** |
| Manual AI | Recommendations / onboarding / API — **works** |

---

## 5. Token cost sources (when `AI_PROVIDER` is real LLM)

1. `AIAnalyticsEngine.execute` / `execute_stream` — provider `complete()`  
2. Invoked by `AIIntelligenceEngine.run_intelligence` (primary product path)  
3. Invoked by legacy `AIService.create_run` / stream  
4. Ops scripts that call `run_intelligence`

Not token sources: digests, todays_focus, ask, list recommendations, dashboard AI embeds, Insight Engine V1.

---

## 6. Architecture (current)

```
Upload → ETL (ledger/aggregates) → PROCESSED → Dashboard analytics
                                              ↘ post_report_ai (NO-OP default)

Seller click «Запустить анализ»
  → POST /ai/intelligence/period-runs
  → AIIntelligenceEngine
      → AIAnalyticsEngine (LLM if provider live)
      → MultiAgentCoordinator / decision / persist AIRecommendation
```

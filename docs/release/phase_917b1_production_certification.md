# Phase 9.17-B1 — Production certification

**Date:** 2026-07-19 (UTC)

## Release identity

| Item | Value |
|------|-------|
| Commit / GitHub / Release / Backend SHA | `6bed70cb23185cd679712a89fa92a5566ebc9123` |
| Branches | `main` == `origin/main` == `release/task0-jam-subscription-expenses` == `origin/release/...` |
| Deploy (backend restart) | **2026-07-19T16:42:08Z** (`marketplace-backend`) |
| Worker restart | **2026-07-19T16:42:10Z** (`marketplace-worker`) |
| Live process env | `AI_AUTO_RECOMMEND_AFTER_REPORT=false`, `AI_ENABLED=true`, `AI_PROVIDER=openai_compatible` |
| Post-deploy smoke | **PASS** |

## Scenario 1 — Finance upload (auto AI must NOT run)

| Check | Result |
|-------|--------|
| Report | `2a2b1073-9869-4e7e-a100-521c4415e08d` (`finance`, 51 rows) |
| Status | **`processed`** (`processed_at` 16:54:29Z) |
| Worker log | **`post_report_ai_skipped_disabled`** at 16:54:30Z |
| `AIRecommendation` count | **unchanged** (2 → 2 after ETL) |
| Auto `run_intelligence` | **not invoked** (no `post_report_ai_recommendation_ok`) |

## Scenario 2 — Explicit «Запустить AI-анализ» (API period-runs)

| Check | Result |
|-------|--------|
| Endpoint | `POST /api/v1/ai/intelligence/period-runs` |
| HTTP | **201 Created** (~13.8 s) |
| Logs | `ai_run_started` → `ai_run_completed` → `ai_intelligence_completed` |
| Recommendations | **2 → 3** |

## Verdict

**CERTIFIED** — Auto AI after finance ETL is off; manual intelligence still works.

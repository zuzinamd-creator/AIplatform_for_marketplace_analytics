## Runtime AI Execution (REAL-AI-1)

### Execution lifecycle (governed)

1. API request → auth/JWT → tenant-scoped DB session
2. `AIOrchestrationService.begin_run()` persists `AIExecutionRun`
3. Context assembled + grounded (metrics snapshot + freshness + degraded signals)
4. Prompt rendered deterministically (templates) + executed via provider adapter
5. Output validated (stale/evidence/unsupported claims)
6. Advisory insight/recommendation persisted (separate from ledgers)
7. `AIOrchestrationService.complete_run()` persists audit events + token/cost fields

### Provider retries and containment

- retries are **bounded**: `AI_MAX_RETRIES`
- circuit breaker can short-circuit to mock provider to keep product usable under provider outage

### Advisory-only guarantee

- AI does not mutate marketplace state
- AI does not mutate ledgers or derived projections
- all writes are to AI advisory tables (`ai_execution_runs`, `ai_insights`, `ai_recommendations`, feedback)


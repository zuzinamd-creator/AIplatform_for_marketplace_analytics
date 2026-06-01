# AI architecture report (Phase 2)

**Date:** 2026-05-26  
**Status:** Production-grade analytics engine on governed foundation.

## Maturity assessment

| Capability | Level | Notes |
|------------|-------|-------|
| Provider abstraction | **L3** | Mock + OpenAI-compatible HTTP; embedding/rerank mocked |
| Analytics workflows | **L3** | 8 workflows mapped to agents/prompts |
| Grounding | **L3** | Evidence refs from `AIInsightInputDTO`; semantics + freshness in prompt |
| Validation | **L2** | Heuristic confidence/stale/unsupported-claim checks |
| Memory | **L2** | Bounded `ai_session_turns`, tenant RLS |
| API | **L3** | JWT + RLS runs/insights endpoints |
| Evaluation | **L2** | Regression runner + unit tests |
| Vector RAG | **L0** | Retrieval is deterministic DTO-based (extensible) |

## Provider abstraction model

```
AIAnalyticsEngine
  → AIOrchestrationService (audit)
  → get_llm_adapter() / get_embedding_adapter() / ...
  → with_provider_retry()
```

Configure via `AI_PROVIDER`, `AI_OPENAI_*`, `AI_PROVIDER_MAX_RETRIES`.

## Hallucination risks

| Risk | Mitigation | Gap |
|------|------------|-----|
| Invented revenue | Validator flags currency claims without DTO revenue | No automatic numeric cross-check |
| Stale rebuild data | `degraded_mode`, confidence cap | Consumers must read flags |
| Prompt injection | `sanitize_user_text` on memory | Report raw strings in DTO not scrubbed yet |
| Overconfident narrative | `confidence_hint` capped when stale | No human review queue |

## Operational risks

| Risk | Control |
|------|---------|
| Provider outage | Retry + fail_run audit |
| Token spend | Per-agent budgets + run totals |
| Tenant abuse | `AI_RATE_LIMIT_PER_MINUTE` |
| Agent misuse | `AI_DISABLED_AGENTS` kill switch |

## Scaling limits

- In-process rate limiter (single instance); move to Redis for multi-replica.
- Session memory trim per write (OK to ~100 RPS per tenant).
- Mock/default provider: no external latency.

## Future evolution

1. Vector retrieval behind `EmbeddingAdapter` + pgvector.
2. Contradiction checks against ledger aggregates (read-only SQL tool).
3. Human approval queue for `requires_human_approval_for` actions.
4. Per-tenant provider routing and cost accounting export.

## Current Prompt + Runtime Execution (REAL-AI-1)

This document describes how AI prompts are currently defined, rendered, executed (provider call), validated, and persisted — **before** introducing real provider streaming + cost tracking.

### Prompt storage and contracts

- Prompts are **not stored in DB**. They are versioned as **in-code contracts** in `app/ai/prompts/registry.py`.
- `PromptRegistry` holds `PromptContract` objects:
  - `prompt_id`, `version`, `purpose`
  - `output_schema` (descriptive)
  - deterministic vs probabilistic sections (governance cues)
- Access path:
  - `app.ai.prompts.get_prompt_contract(prompt_id)` → `PromptRegistry.get(prompt_id)`

**Key implication:** “prompt templates” today are only **contracts**; the actual LLM input string is built ad-hoc in engines (system prompt + JSON metrics snapshot).

### Where provider execution is injected

Provider execution is called inside the engines, via adapters.

- Provider selection:
  - `app/ai/providers/factory.py:get_llm_adapter()`
    - primary: `settings.ai_provider` (default `mock`)
    - optional fallback: `settings.ai_failover_provider`
    - circuit breaker gating: `GLOBAL_CIRCUIT_BREAKERS.allow("ai_provider")`
- Adapter interface:
  - `app/ai/providers/base.py: LLMAdapter.complete(request: LLMRequest) -> LLMResponse`
  - request/response DTOs: `app/ai/providers/types.py`

### Current mock provider behavior

`app/ai/providers/mock.py:MockLLMAdapter.complete()` returns deterministic JSON:

- `summary`, `bullets`, `confidence_hint`, `disclaimer`
- includes rough token counts and latency, but no cost tracking

### OpenAI-compatible provider (already present, non-streaming)

`app/ai/providers/openai_compatible.py:OpenAICompatibleLLMAdapter` performs:

- HTTP `POST {AI_OPENAI_BASE_URL}/chat/completions`
- reads `choices[0].message.content`
- reads `usage.prompt_tokens` / `usage.completion_tokens`

**Gap:** no streaming support, no structured retry/audit events, no cost persistence.

### AIAnalyticsEngine execution flow (insight generation)

File: `app/ai/analytics/engine.py`

1. **Governance pre-checks**
   - kill switches / overload containment (`_assert_ai_runtime_allowed`)
   - tenant rate limit (`check_tenant_rate_limit`)
   - workflow spec + prompt_id match (`spec_for`)
2. **Run orchestration (audit row)**
   - `AIOrchestrationService.begin_run()` persists `AIExecutionRun`
   - prompt version resolved via `PromptRegistry`
3. **Context + grounding**
   - `AIContextAssembler.assemble()` → `build_grounded_context()`
4. **Prompt rendering (current)**
   - system prompt via `_build_system_prompt(...)`
   - user message = JSON dump of `grounded.metrics_snapshot` truncated to 6000 chars
5. **Provider call**
   - `llm = get_llm_adapter()`
   - bounded retries: `with_provider_retry(...)` using `settings.ai_provider_max_retries`
6. **Validation**
   - `validate_insight_output(...)` parses JSON and enforces stale/evidence/unsupported-claim rules
7. **Persistence**
   - advisory insight stored in `AIInsight` (tenant-scoped)
   - run completion persisted in `AIExecutionRun` via `AIOrchestrationService.complete_run(...)`

### How outputs are validated

- Insight validation: `app/ai/validation/insight_validator.py`
  - requires JSON keys: `summary`, `bullets`, `confidence_hint` (best effort; falls back)
  - penalizes confidence when:
    - stale/degraded context
    - numeric currency claims without evidence
    - missing evidence refs
- Recommendation validation: `app/ai/validation/recommendation_validator.py`
  - checks contradictions (e.g., high confidence without evidence)
  - checks stale context vs urgency language

### Recommendation generation (intelligence)

File: `app/ai/intelligence/engine.py`

- Runs analytics engine first (produces `ValidatedInsightDTO`)
- Builds grounded context, then coordinates multi-agent decision (`MultiAgentCoordinator`)
- Applies policy gating (`classify_and_gate`)
- Persists `AIRecommendation` (tenant-scoped)

Post AI-USEFULNESS:

- Quality post-processing adds:
  - fingerprint in `lineage`
  - why/action/impact fields in `action_plan`
  - confidence normalization + duplicate suppression

### Current auditability and isolation guarantees

- **Tenant isolation**: enforced by RLS + `TenantSession.transaction(...)`
- **Advisory-only**: engines never mutate ledger tables; insights/recommendations are separate advisory tables
- **Auditability**:
  - `AIExecutionRun` row per run (prompt_id/version, budgets, tool call count, error, timing, events)
  - metrics events via `emit_ai_metric(...)`


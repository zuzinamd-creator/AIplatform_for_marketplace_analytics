## Prompt Runtime Architecture (REAL-AI-1)

This phase formalizes prompt runtime behavior into **two layers**:

1. **Prompt contracts** (governance) — what the prompt is allowed to do and what shape it must return.
2. **Prompt templates** (rendering) — deterministic string construction for provider execution.

### Contracts (existing)

`app/ai/prompts/registry.py`

- versioned `PromptContract` per `prompt_id`
- deterministic vs probabilistic section labels

### Templates (new)

`app/ai/prompts/runtime.py`

- deterministic rendering: system prompt + user metrics JSON
- stable template identifier + version for auditability

### Rendering guarantees

- variable injection is explicit (grounded context + workflow)
- rendering is deterministic for the same grounded inputs
- truncation is bounded (metrics payload capped)

### Why this matters

It decouples:

- governance review (contract changes)
- prompt text iteration (template changes)

while keeping the **advisory-only** and **auditability** guarantees intact.


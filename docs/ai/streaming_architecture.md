## Streaming Architecture (REAL-AI-1)

This repo uses **Server-Sent Events** (SSE) for streaming AI output.

### Backend

Endpoint:

- `POST /api/v1/ai/runs/stream`

Behavior:

- streams JSON events as SSE frames:
  - `{"type":"delta","text":"..."}`
  - `{"type":"final","run_id":"...","insight_id":"...","summary":"...","confidence":"..."}`
  - `{"type":"error","message":"..."}`

Implementation:

- `AIAnalyticsEngine.execute_stream()` yields events while the provider streams
- `OpenAICompatibleLLMAdapter.stream()` parses `data: {json}` lines from the upstream provider

### Frontend

Page:

- `frontend/src/views/ai/RecommendationsPage.tsx`

Implementation:

- `fetch()` POST to `/ai/runs/stream`
- reads `ReadableStream` chunks
- parses SSE frames by splitting on `\\n\\n`
- supports cancellation via `AbortController`

### Guarantees

- run remains **advisory-only**
- execution still goes through AI governance lifecycle (`begin_run` → `complete_run` / `fail_run`)
- RLS enforced by normal request auth + DB session scoping


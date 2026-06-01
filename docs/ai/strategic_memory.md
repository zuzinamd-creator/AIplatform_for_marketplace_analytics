# Strategic Memory

Long-lived tenant analytical memory is stored in `ai_strategic_memory` via `StrategicMemoryStore` (`app/ai/memory/strategic.py`).

## Governance

| Rule | Implementation |
|------|----------------|
| Tenant isolation | RLS on `user_id` |
| Deduplication | SHA-256 `content_hash` per `memory_key` |
| Non-authoritative | Memory does not override ledgers or semantics registry |
| Lineage | `source_run_id` links to `ai_execution_runs` |

## Recall

`StrategicMemoryStore.recall(memory_key)` returns recent entries for planner/analyst context expansion (bounded limit).

## Semantic versioning

Each row stores `semantics_version` aligned with platform semantics contracts.

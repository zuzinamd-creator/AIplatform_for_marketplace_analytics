# Platform stabilization report (Phase 1)

**Date:** 2026-05-26  
**Scope:** Entropy reduction without architecture redesign.

## What was cleaned

| Area | Change |
|------|--------|
| **WB persist** | Split `app/etl/wb/persist.py` into `persist_layers.py`, `persist_aggregates.py`; facade class unchanged |
| **ETL pipeline** | Split legacy analytics → `pipeline_analytics.py`; CLI → `pipeline_standalone.py`; core `pipeline.py` ~240 LOC |
| **API → ETL** | `app/api/reports.py` now uses `app/services/report_upload_service.py` (no direct ETL imports) |
| **Ruff** | Auto-fixed 108 import/format issues; E501 scoped to tests/parsers/alembic |
| **Mypy** | Fixed 25 errors across app + tests; expanded `pyproject.toml` to `files = ["app", "tests"]` |
| **Integration DB** | `truncate_integration_tables` skips tables not yet migrated |
| **Governance** | Stricter layer rules (services/runtime/api); forbidden raw `db.commit` in API; stabilization doc required |
| **Tests** | Generator fixture types; queue idempotency key default; integration helper return casts |

## Validation baseline

```bash
pytest tests/unit -q
pytest tests/integration -m integration --ignore=tests/integration/stress
ruff check .
mypy app tests
python scripts/architecture_governance_check.py
```

## Remaining technical debt

| Item | Severity | Blocker |
|------|----------|---------|
| E501 line length in `app/` | Low | Scoped per-file ignores in `pyproject.toml`; trim when touching files |
| `UP042` StrEnum migration | Low | Globally ignored until dedicated PR (17 enums) |
| `inventory_consistency_verification.py` LOC | Medium | Grandfathered >200 LOC; split when next touched |
| `operations/recovery.py` LOC | Medium | Grandfathered; split into recovery_steps/* when touched |
| Domain `analytics_payload` → `app.etl.types` | Low | Allowlisted cross-layer import; move to `app/dto` later |
| Full-repo strict mypy (`disallow_untyped_defs`) | Medium | Requires typing pandas-heavy ETL paths |
| Integration suite runtime (~9 min) | Low | Parallel CI shards; not correctness |

## Architectural risks (unchanged invariants)

- Append-only ledgers, advisory locks, staging-promote, RLS, semantics governance **unchanged**.
- No runtime/orchestration logic rewrites.
- AI layer remains advisory-only.

## Unresolved coupling

- `app/services/report_upload_service.py` still delegates to ETL loaders (correct layer: API → services → etl).
- `app/domain/inventory/analytics_payload.py` depends on `AnalyticsPayload` TypedDict in `app/etl/types.py`.

## Operational stability

- Structured log event names unchanged (`emit_etl_metric`, `emit_ai_metric`, runtime `log_runtime_event`).
- Kill switches: `AI_ENABLED`, `ORCHESTRATOR_ENABLED` documented in README §19.
- Integration tests deterministic given migrated DB (`alembic upgrade head`).

## Next stabilization targets

1. Split `inventory_consistency_verification.py` into verify + persist submodules.
2. Move `AnalyticsPayload` to `app/dto/analytics_payload.py` and drop domain→etl allowlist.
3. Enable `UP042` enum migration in a dedicated PR.
4. Add CI job matrix: unit (fast) + integration (postgres service).

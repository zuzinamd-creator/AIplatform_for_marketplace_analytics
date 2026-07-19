# AI trigger policy (Phase 9.17-B · re-certified 9.17-F)

## Product rule

1. Seller uploads a marketplace report.  
2. ETL builds ledgers, snapshots, and analytics aggregates (9.17-E Safe Incremental Stream for inventory).  
3. Report becomes **`processed`** — dashboard KPIs/charts are available.  
4. **AI analysis starts only** when the seller explicitly clicks **«Запустить анализ»** (or calls the AI intelligence API).

Automatic AI after every upload is **disabled by default** to avoid token spend and worker queue delay. Re-certified production: `AI_AUTO_RECOMMEND_AFTER_REPORT=false` → worker logs `post_report_ai_skipped_disabled`.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `AI_ENABLED` | `true` | Master switch for any AI runs |
| `AI_AUTO_RECOMMEND_AFTER_REPORT` | **`false`** | If `true`, legacy post-ETL auto `revenue_insight` still runs |

Code: `app/core/config.py` · hook: `app/etl/post_report_ai.py` · worker still calls the hook, which **no-ops** when auto is off (logs `post_report_ai_skipped_disabled`).

## Explicit launch paths (still active)

| Path | Entry |
|------|--------|
| UI | `/app/ai/recommendations` → «Запустить анализ» |
| API | `AIService.run_intelligence` / `run_intelligence_for_period` via `app/api/ai.py` |

## What does **not** require AI

Dashboard Overview: KPIs, charts, Top SKU, Financial Summary, Business Signals, deterministic Insight Engine V1 captions — all work from governed analytics without `AIRecommendation`.

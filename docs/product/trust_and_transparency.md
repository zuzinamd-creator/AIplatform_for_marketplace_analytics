# Trust & Transparency UX (UX-3)

## Design principle

Users must always understand **what the system knows**, **what it does not know**, and **when AI may be wrong**.

## Implemented UX elements

### 1) Global trust banners (`TrustBanners`)

Shown in the app shell on every authenticated page. Derived from:

- `GET /api/v1/ops/runtime/summary` (queue, rebuild, health)
- `GET /api/v1/ai/operational/status` (degraded intelligence mode)
- `GET /api/v1/reports` (failed uploads)

Banner types:

| Banner | When shown | User message |
|--------|------------|--------------|
| Rebuild in progress | `rebuild.running > 0` | KPIs may be temporarily stale |
| Data refresh pending | `rebuild.pending_dispatch > 0` | Analytics may reflect older snapshots |
| Processing failures | `dead_letter_count > 0` | Review upload history |
| Reports processing | queue active | Dashboard may update shortly |
| Upload failed | report status failed | Re-check file format |
| AI cautious mode | `degraded_intelligence_mode` | Verify evidence before acting |
| Data outdated | tenant/workload stale/degraded | Treat outputs with caution |
| All clear | no incidents | Normal operation |

User preferences in **Settings** can disable stale/rebuild/AI degraded alerts.

### 2) System status page (`/app/status`)

Seller-friendly aggregation — no raw JSON required. Includes:

- Upload processing counts
- Rebuild state
- AI readiness (normal vs cautious)
- “What this means for you” guidance

### 3) AI transparency notice

Shown on recommendation detail pages:

- AI is advisory only (no ledger mutation)
- Evidence must be verified
- Degraded mode explanation
- Feedback improves relevance, not governance bypass

### 4) Recommendation trust UX

On recommendation detail:

- Confidence and risk badges
- “Why this matters” framing
- Suggested action steps
- Usefulness rating (1–5) + accept/reject rationale

## When AI may be wrong (user-facing copy)

- Data is stale or rebuilds are pending
- Costs or SKU mappings are incomplete
- Report failed or partially processed
- Confidence is low or approval is required
- Explainability evidence does not match seller’s ground truth

## When data is outdated

Signals:

- Rebuild running/queued
- Tenant/workload state indicates stale/degraded
- AI operational status in cautious mode

User action: wait for processing, upload newer report, check System status.

## When recommendations require caution

- `requires_human_approval = true`
- Low confidence score
- Degraded intelligence mode active
- Missing or thin explainability evidence

## Future improvements (not UX-3)

- Render evidence graph as linked SKU/report references (not JSON)
- Staleness timestamp (“data as of …”) on dashboard KPIs
- Inline “why am I seeing this banner?” help tooltips

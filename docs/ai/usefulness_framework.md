# AI Usefulness Framework (REAL-AI-V4B)

Seller-oriented evaluation of AI recommendations — separate from model accuracy or token cost.

## Goals

- Measure whether sellers **act on** advice, not whether the LLM sounded confident
- Detect **fatigue** (repeated, ignored, dismissed patterns)
- Improve **prioritization** and **daily focus** over time

## Core metrics

| Metric | Source | Meaning |
|--------|--------|---------|
| Acceptance rate | `ai_recommendation_feedback` (`accept`) | Seller agreed advice is relevant |
| Ignored (7d) | Active recs with no feedback after 7 days | Low engagement |
| Action completion | `seller_workflow_state = completed` | Seller marked done |
| Repeated dismissals | `dismissed` count | Strong negative signal |
| Usefulness score | Composite in `compute_usefulness_metrics` | Weighted accept + completion vs ignores/dismissals |
| Helpful rate | Feedback `helpful=true` ratio | Qualitative satisfaction |
| Feedback trend | `improving` / `stable` / `needs_attention` | Derived from helpful rate |

API: `GET /api/v1/ai/usefulness/metrics`

## Recommendation lifecycle

1. **Generate** — intelligence run → `apply_quality` → actionable `seller_usefulness` payload
2. **Prioritize** — `compute_seller_priority` → tier: `today` | `this_week` | `informational`
3. **Fatigue check** — `assess_fatigue` before persist; suppress duplicate if repeat threshold hit
4. **Present** — Today's Focus, inbox tiers, detail page
5. **Workflow** — complete / snooze / dismiss / save
6. **Feedback** — accept / reject / helpful rating

## Fatigue reduction

Implemented in `app/ai/product/fatigue.py`:

- **Fingerprint** dedupe (quality engine)
- **Cooldown** (3 days after repeat)
- **Decay** (priority penalty per 7d repeat)
- **Suppress** (≥4 repeats in 7d → reuse existing row)
- **Novelty score** (reduces confidence on repeats)

## Prioritization model

`app/ai/product/prioritization.py` combines:

- Revenue opportunity score
- Urgency score (seller usefulness)
- Confidence
- Anomaly / inventory workflow boosts
- Stale/degraded context
- Novelty minus fatigue penalty

Tiers:

- **today** — score ≥ 72 or urgency ≥ 80
- **this_week** — score ≥ 48 or urgency ≥ 55
- **informational** — otherwise

## Impact estimation rules

`app/ai/product/impact_estimation.py`:

- Only **range labels** and **confidence bands**
- Evidence refs from grounded context
- `do_not_trust_exact_amounts: true` always
- Never invent precise revenue/margin numbers

## Daily assistant

`TodaysFocusService` (`GET /api/v1/ai/todays-focus`):

- Requires attention today / can wait / dangerous / highest upside
- Top 3 actions, critical alerts, quick wins
- Priority queue (sorted by recommendation score)

UI: `/app/ai/today`

## Evaluation checklist (seller testing)

- [ ] Today's Focus matches inbox tiers
- [ ] Impact text reads as ranges, not forecasts
- [ ] Repeated runs do not flood inbox (fatigue suppress)
- [ ] Complete/dismiss updates usefulness metrics
- [ ] Anomaly workflow surfaces in "dangerous" when urgency high

## Related docs

- `docs/product/ai_usefulness_metrics.md`
- `docs/product/recommendation_lifecycle.md`
- `docs/product/ai_assistant_workflows.md`

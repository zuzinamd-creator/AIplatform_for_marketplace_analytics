# Recommendation Lifecycle

```
Intelligence run → AIRecommendation (draft/pending_approval)
  → seller_usefulness enriched action_plan
  → seller_workflow_state: active (inbox)
  → seller actions: save | snooze | dismiss | complete
  → feedback: accept | reject | note
  → superseded by newer run (optional, governance)
```

## States

**Governance status** (`status`): draft, pending_approval, approved, rejected, superseded

**Seller workflow** (`seller_workflow_state`): active, saved, snoozed, dismissed, completed

Snoozed items auto-return to `active` when `snoozed_until` passes (on list fetch).

## Usefulness payload

Stored in `action_plan.seller_usefulness`:

- why_this_matters, expected_business_impact, urgency
- estimated_upside, estimated_downside
- concrete_next_action, confidence_explanation, limitations

## Audit

- `reasoning_trace` (multi-layer + domain_insights)
- `lineage.fingerprint` for dedupe and fatigue tracking

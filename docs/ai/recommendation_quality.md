## Recommendation Quality Engine (AI-USEFULNESS)

This project treats AI recommendations as **advisory outputs**: they must be seller-readable, evidence-linked, and safe under stale/degraded data conditions.

### What changed

- **Quality post-processing (no new orchestration)**: `app/ai/quality/recommendation_quality.py`
  - Computes a stable **fingerprint** for repetition/duplication detection.
  - Normalizes confidence under:
    - stale/degraded context
    - missing evidence
    - generic wording
    - contradictions / unsupported claims
  - Produces explicit fields:
    - `why_this_matters`
    - `recommended_action`
    - `impact_estimate`
- **Duplicate suppression**: `app/ai/intelligence/engine.py`
  - If the same fingerprint already exists for the tenant, reuse the existing recommendation ID.
  - Reduces fatigue without changing core AI decision logic.

### Fingerprint model

Fingerprint is a SHA-256 of:

- workflow
- normalized title + summary
- sorted evidence source IDs

Stored in `AIRecommendation.lineage["fingerprint"]` (JSONB) to avoid migrations.

### Confidence normalization rules (summary)

Starting from model confidence \(c \in [0, 1]\), apply multiplicative penalties:

- stale/degraded context: \(\times 0.75\)
- no evidence: \(\times 0.70\)
- generic short advice: \(\times 0.80\)
- contradictions: \(\times 0.60\)
- unsupported claims: \(\times 0.65\)

Then clamp to \([0, 1]\).

### Before/after example (shape)

- **Before**: “Consider optimizing prices to improve margin.”
  - no explicit evidence linkage
  - generic verb phrasing
  - no action steps
- **After** (stored in `action_plan`):
  - `why_this_matters`: “Signals suggest data may be stale; this recommendation is advisory and should be verified.”
  - `recommended_action`: “Open Explainability → confirm evidence → apply the change outside the platform → record feedback.”
  - `impact_estimate`: includes normalized confidence + priority + opportunity score


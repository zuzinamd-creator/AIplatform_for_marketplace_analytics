## AI Usefulness Report (AI-USEFULNESS)

### Summary

This phase improves **usefulness, clarity, actionability, and trust** without changing core orchestration or adding new agents.

### Findings (audit)

- **Repetition risk**: recommendations can repeat across runs and sellers (no stable grouping previously).
- **Generic wording**: short advice with “optimize / consider / improve” tends to be non-actionable.
- **Evidence gaps**: high confidence without evidence references increases hallucination risk.
- **Stale-context contradictions**: urgency language (“immediate action”) under rebuild/degraded context reduces trust.

### Implemented improvements

- **Recommendation quality engine**:
  - confidence normalization under stale/no-evidence/generic/contradiction conditions
  - explicit `why_this_matters` and `recommended_action`
  - stable fingerprint for repetition and fatigue measurement
  - duplicate suppression by fingerprint
- **Feedback loop stats**:
  - `GET /api/v1/ai/recommendations/stats` returns:
    - `avg_rating`, `helpful_rate`, accept/reject rates
    - `ignored_7d` (no-feedback after 7 days)
    - most frequent fingerprints (fatigue proxy)
- **Explainability UX**:
  - evidence nodes rendered as readable items
  - “why/action” visible in primary recommendation surface (when provided by backend)

### Seller evaluation scenarios (recommended)

Use `docs/product/real_data_scenarios.md` for data setup and run these checks:

- **Daily routine**: upload report → dashboard KPIs → 3 AI recommendations → accept/reject with rationale.
- **Stale mode**: trigger rebuild/backlog → verify confidence decreases and language is cautious.
- **Repetition**: run intelligence multiple times → confirm fingerprint reuse reduces duplicates.

### Hallucination risk review (current mitigations)

- Penalize confidence without evidence references.
- Penalize contradictions/unsupported claims.
- Visible explainability: evidence nodes + reasoning trace.


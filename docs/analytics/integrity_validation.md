# Integrity validation (deterministic)

This document describes the **backend integrity validator** that detects impossible KPI states and surfaces seller-facing warnings.

## Design constraints

- **No architecture redesign**
- **Tenant-scoped (RLS)**
- **Read-only** validation (SELECT-only)
- **Deterministic**: no AI, no heuristics that depend on external data

## Implementation

- Service: `app/services/financial_integrity_service.py`
- Output: `AnalyticsIntegrityMeta` with `warnings[]` and optional `financial_completeness_score`
- Wired into analytics read APIs via `AnalyticsService`

## Warning model

Each warning is:

- `code`: stable identifier (used by UX)
- `severity`: `info` | `warning` | `critical`
- `message`: seller-readable short explanation
- `context`: optional key/value metadata

## Current validations (minimum set)

- `profit_gt_revenue` (**critical**): profit exceeds revenue in selected period
- `negative_revenue` (**critical**): revenue is negative
- `abnormal_margin` (**warning**): margin outside [-100%; 100%]
- `missing_cost_basis` (**warning**): no `cost_history` rows (profit/margin not governed)
- `payout_reconciliation_mismatch` (**warning**): report reconciliation differences exist

## Where warnings appear

Analytics responses include:

- `freshness` (existing)
- `integrity` (new, additive)

No endpoint performs silent corrections; warnings are explicit.


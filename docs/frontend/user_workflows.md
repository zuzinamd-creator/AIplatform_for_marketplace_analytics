# Seller Workflows (UX-1)

This document describes the seller-facing workflows implemented in the `frontend/` app during **PHASE UX-1**.

## 1) Onboarding & sign-in

- **Register**: `/register` → `POST /api/v1/auth/register`
- **Login**: `/login` → `POST /api/v1/auth/login` → token stored locally → `GET /api/v1/auth/me`
- **Tenant identity**: shown in the app shell (email + user id). Tenancy isolation is enforced by backend RLS.

## 2) Main dashboard (operational-first)

Route: `/app/dashboard`

Purpose:

- Provide at-a-glance readiness and operational signals while financial KPI APIs are not yet available.

Current data sources:

- Recent uploads: `GET /api/v1/reports`
- Queue visibility: `GET /api/v1/ops/queue` (uses `status_counts` when available)
- Runtime summary: `GET /api/v1/ops/runtime/summary`
- AI ops: `GET /api/v1/ai/operational/status`

## 3) Report upload flow

Route: `/app/reports/upload`

Steps:

1. Seller selects `marketplace`, `report_type`
2. Drag-and-drop file into the dropzone
3. Upload begins; UI displays progress
4. Backend validates content:
   - If checksum already exists → returns existing report + message
   - Otherwise: creates report row and enqueues ETL job
5. UI links seller to reports list / processing state

API:

- `POST /api/v1/reports/upload` with multipart form:
  - `marketplace`
  - `report_type`
  - `file`

## 4) Upload history & processing lifecycle

Routes:

- `/app/reports` (list)
- `/app/reports/:reportId` (detail)

Purpose:

- Make the pipeline lifecycle visible to the seller:
  - `pending` / `processing` / `processed` / `failed`
  - job snapshot and latest error message

APIs:

- `GET /api/v1/reports`
- `GET /api/v1/reports/{id}`

## 5) AI recommendations and operator feedback

Routes:

- `/app/ai/recommendations`
- `/app/ai/recommendations/:recommendationId`

Goals:

- Present recommendations as **actions** with:
  - summary
  - confidence
  - approval requirement
  - explainability (evidence graph + reasoning trace)

APIs:

- `GET /api/v1/ai/recommendations`
- `GET /api/v1/ai/recommendations/{id}`
- `GET /api/v1/ai/recommendations/{id}/explainability`
- `POST /api/v1/ai/recommendations/{id}/feedback`

## 6) Operational visibility (read-only)

Routes:

- Queue: `/app/ops/queue`
- Dead letters: `/app/ops/dead-letters`
- Rebuild lifecycle: `/app/ops/rebuilds`
- Drift checks: `/app/ops/drift-checks`
- Anomalies: `/app/ops/anomalies`
- Runtime health: `/app/ops/runtime/health`
- Runtime summary: `/app/ops/runtime/summary`
- Semantics status: `/app/ops/semantics`

Key constraint:

- These pages are **read-only** and must stay that way when the backend endpoint is read-only.


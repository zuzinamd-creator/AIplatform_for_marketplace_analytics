# Seller onboarding (UX-2)

## Goals

- Minimal cognitive load
- Progressive disclosure (“only the next thing”)
- Clear actions that unlock real value

## Implemented flow (frontend)

Route: `/app/onboarding`

Steps:

1. **Welcome**
2. **Workspace profile** (client-side `localStorage` for UX-2)
3. **Marketplace selection** (client-side preference for UX-2)
4. **First report upload** → `/app/reports/upload`
5. **SKU mapping guidance** (documented; backend CRUD endpoints not exposed yet)
6. **Cost import** → `/app/costs`
7. **First AI analysis** → `POST /api/v1/ai/intelligence/runs`
8. **Dashboard walkthrough**

## State model

- Completion flag: `localStorage["ma.onboardingDone"]`
- Workspace profile: `localStorage["ma.workspaceProfile"]`

## Backend contracts used

- `GET /api/v1/auth/me`
- `GET /api/v1/reports`
- `GET /api/v1/costs`
- `GET /api/v1/ai/runs`
- `POST /api/v1/ai/intelligence/runs` (defaults to workflow `inventory_insight` + prompt `inventory.insight.v1`)


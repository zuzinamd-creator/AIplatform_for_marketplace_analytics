# Seller onboarding (UX-2)

## Goals

- Minimal cognitive load
- Progressive disclosure (“only the next thing”)
- Clear actions that unlock real value

## Account creation vs seller onboarding

These are **two separate flows**:

| Flow | When | Route / API |
|------|------|-------------|
| **Invite registration** (Phase 9.3A) | Before first login — account does not exist yet | `/register?invite=…` → validate → register |
| **Seller onboarding wizard** (UX-2) | After first login — account exists, workspace setup | `/app/onboarding` |

### Invite registration (pre-login)

```
platform_admin → create invite → invite link
  → seller: validate → register → seller account
  → seller logs in
```

See [user_workflows.md](../frontend/user_workflows.md) for invite lifecycle (used / expired / revoked).

**Legacy / emergency account creation** (`scripts/create_mvp_test_user.py`, direct DB insert) is not the production path — use **Администрирование → Приглашения**.

## Implemented flow (frontend — post-login)

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

## Admin onboarding (platform_admin)

Platform operators with `platform_admin` role also see **Администрирование** in the shell:

- **Пользователи** — inspect registered accounts
- **Приглашения** — create and revoke seller invites

Creating an invite is the **first step** for onboarding a new external seller.

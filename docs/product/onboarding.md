# Seller onboarding (F1.6 · certified Phase 9.18-F2-C3)

## Goals

- Minimal cognitive load
- Progressive disclosure (“only the next thing”)
- Clear actions that unlock real value on the financial panel

## Account creation vs seller onboarding

These are **two separate flows**:

| Flow | When | Route / API |
|------|------|-------------|
| **Invite registration** (Phase 9.3A) | Before first login — account does not exist yet | `/register?invite=…` → validate → register |
| **Seller onboarding wizard** (F1.6) | After first login — account exists, workspace setup | `/app/onboarding` |

### Invite registration (pre-login)

```
platform_admin → create invite → invite link
  → seller: validate → register → seller account
  → seller logs in
```

See [user_workflows.md](../frontend/user_workflows.md) for invite lifecycle (used / expired / revoked).

**Legacy / emergency account creation** (`scripts/create_mvp_test_user.py`, direct DB insert) is not the production path — use **Администрирование → Приглашения**.

## Certified wizard flow (frontend — post-login)

Route: `/app/onboarding`

| # | Step ID | Title (UI) | Required | Notes |
|---|---------|------------|----------|-------|
| 1 | `value-intro` | Добро пожаловать | Yes | Value framing; no data entry |
| 2 | `workspace` | Профиль рабочего пространства | **Optional** | «Пропустить» continues wizard |
| 3 | `marketplace` | Выбор маркетплейса | Yes | Cannot advance while `marketplace === unknown` |
| 4 | `upload` | Первая загрузка отчёта | Yes | Deep-link to `/app/reports/upload` |
| 5 | `processing` | Обработка отчёта | Yes | Polls report status until `processed` or `failed` |
| 6 | `cost_import` | Загрузка себестоимости | **Optional** | «Пропустить» continues wizard; link to `/app/costs` |
| 7 | `complete` | Готово | Yes | Primary exit to analytics panel |

### Removed steps (not in wizard)

The following **UX-2** steps were removed in Phase 9.18-F2-C1 and are **not reachable** in the wizard:

- `sku_mapping` — SKU mapping guidance
- `first_ai` — automatic first AI analysis
- `walkthrough` — analytics walkthrough as a mandatory step

### Optional steps

| Step | Skip control | Behavior |
|------|--------------|----------|
| `workspace` | «Пропустить» | Advances to `marketplace` without saving (save is also available) |
| `cost_import` | «Пропустить» | Advances to `complete` |

### Processing step

After upload, the seller sees seller-friendly status (no ETL job IDs):

| Phase | Seller message |
|-------|----------------|
| `pending` | Отчёт принят |
| `uploaded` | Файл загружен |
| `processing` | Обрабатываем данные |
| `processed` | Отчёт готов |
| `failed` | Ошибка обработки |

**Polling:** `GET /api/v1/reports` (latest) → `GET /api/v1/reports/{id}` every 3s via react-query. Polling **stops** when status is `processed` or `failed`.

**CTAs on processing:**

| Status | Button | Effect |
|--------|--------|--------|
| `processing` / `uploaded` / `pending` | «Открыть панель позже» | `setOnboardingDone(true)` → `/app/analytics` |
| `processed` | «Открыть панель» | `setOnboardingDone(true)` → `/app/analytics` |
| `failed` | «Попробуйте загрузить файл снова» | Returns to `upload` step |

«Далее» on the processing step is shown only after `processed`, allowing continuation to optional `cost_import`.

### Complete step and dashboard entry

Primary CTA: **«Открыть панель»** → `localStorage["ma.onboardingDone"] = true` → `/app/analytics`.

Secondary optional link: **ИИ-помощник** → `/app/ai/recommendations` (destination only — **no AI run** triggered by the wizard).

Global footer link **«Пропустить и перейти к панели»** navigates to `/app/analytics` without setting the completion flag (seller may still see setup prompts until an explicit finish CTA is used).

### Post-onboarding expectations

On `/app/analytics` (Dashboard P0 certified, F2-B.1), sellers see:

- Period selector → Primary answer (revenue / profit) → Action Strip → Top SKU
- `FirstRunChecklist` hidden when `ma.onboardingDone === true`

Sellers should recognize three margin labels: **Маржа по выплате**, **Маржа SKU**, **Маржа (юнит-экономика)** — see [margin_semantics.md](margin_semantics.md).

## AI policy in onboarding

Onboarding **never** triggers AI automatically. See [ai_trigger_policy.md](ai_trigger_policy.md).

- No `POST /api/v1/ai/intelligence/runs` from the wizard
- AI is available only as an **optional link** on the `complete` step and via normal nav (**Действия → ИИ-помощник**)

## State model

| Key | Storage | Purpose |
|-----|---------|---------|
| `ma.onboardingDone` | `localStorage` | Wizard completion flag |
| `ma.workspaceProfile` | `localStorage` | Workspace name + marketplace preference |

Completion is **client-side only** (no server-side onboarding state).

## Backend contracts used

| API | Used for |
|-----|----------|
| `GET /api/v1/auth/me` | Login redirect (onboarding vs analytics) |
| `GET /api/v1/reports` | Upload detection + processing poll (latest report) |
| `GET /api/v1/reports/{id}` | Processing status detail + poll |
| `GET /api/v1/costs` | Cost import detection on `cost_import` step |

**Not used by onboarding wizard:** `POST /api/v1/ai/intelligence/runs`, `GET /api/v1/ai/runs`.

## Login redirect

| Condition | Destination |
|-----------|-------------|
| Seller, `ma.onboardingDone !== true` | `/app/onboarding` |
| Seller, onboarding complete | `/app/analytics` |
| `platform_admin` | `/app/analytics` (default) |

## Shell integration

When `ma.onboardingDone === true`:

- Nav item **Настройка** (`/app/onboarding`) hidden from **Аккаунт** section
- Sidebar “Завершите настройку” banner hidden
- `FirstRunChecklist` on dashboard hidden

## Admin onboarding (platform_admin)

Platform operators with `platform_admin` role also see **Администрирование** in the shell:

- **Пользователи** — inspect registered accounts
- **Приглашения** — create and revoke seller invites

Creating an invite is the **first step** for onboarding a new external seller.

## Certification references

| Phase | Scope |
|-------|--------|
| F2-C1 | Flow reduction — forbidden steps removed |
| F2-C2 | Processing step + polling |
| F2-C3 | Final onboarding certification audit — **GO** |
| F2-B.1 | Dashboard P0 certified (unchanged by onboarding work) |

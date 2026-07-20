# Demo Environment (UX-3)

## Purpose

Prepare a **portfolio-ready demo** that shows real workflows without exposing internal operator tooling.

## Demo tenant setup

### 1) Create demo seller account

**Production (`REGISTRATION_MODE=invite_only`) — recommended:**

1. Log in as `platform_admin`
2. Navigate **Администрирование → Приглашения**
3. Create invite for demo email → copy invite link
4. Open link in incognito → complete registration → log in

**Local dev with `REGISTRATION_MODE=open`:**

```bash
# Register via UI: /register (no invite token required)
# Suggested credentials for demos (change in production):
# email: demo_seller@example.com
# password: demo_password_123
```

**Legacy / emergency only** (not for portfolio demos):

- `scripts/create_mvp_test_user.py`
- Direct DB insert into `users`

Do **not** use operator scripts for normal production onboarding — use the invite flow above.

Or use validation script (API smoke — **not** the onboarding wizard):

```bash
python scripts/ux2_real_data_validation.py \
  --email demo_seller@example.com \
  --password demo_password_123 \
  --report-file path/to/real_wb_export.csv \
  --costs-file docs/product/fixtures/sample_costs.csv \
  --run-ai   # optional: explicit AI API probe after ETL — not an onboarding step
```

### 2) Enable demo mode

In the frontend:

- **Settings → Product mode → Demo**
- Or set `VITE_PRODUCT_MODE=demo` in `frontend/.env.local`

Demo mode shows a showcase path on the dashboard.

### 3) Complete onboarding (F1.6 wizard)

Navigate `/app/onboarding` and walk through the certified flow:

1. **value-intro** — welcome framing
2. **workspace** (optional) — demo name e.g. “WB Seller Demo”
3. **marketplace** — select Wildberries or Ozon
4. **upload** — open `/app/reports/upload`, upload a sanitized export
5. **processing** — wait for «Отчёт готов» (or use «Открыть панель позже»)
6. **cost_import** (optional) — import `docs/product/fixtures/sample_costs.csv` via `/app/costs`
7. **complete** — «Открыть панель» → `/app/analytics`

**Not part of onboarding:** SKU mapping step, mandatory first AI analysis, or analytics walkthrough step. AI is shown separately in step 8 of the demo script below.

## Demo walkthrough script (15 minutes)

Journey: **Upload → Processing → Dashboard** (onboarding) then optional AI deep-dive.

| Step | Route | Talking point |
|------|-------|---------------|
| 1 | `/login` | Multi-tenant SaaS; each account is RLS-isolated |
| 2 | `/app/onboarding` | F1.6 wizard: value intro → marketplace → upload → **processing** → complete |
| 3 | `/app/reports/upload` | Drag-drop; duplicate detection; governed ETL |
| 4 | `/app/onboarding` (processing) | Seller-friendly processing status; polling until ready |
| 5 | `/app/analytics` | Dashboard P0: revenue, Action Strip, Top SKU (canonical panel) |
| 6 | `/app/reports` | Full processing lifecycle in reports list |
| 7 | `/app/costs` | Costs unlock margin accuracy (optional during onboarding) |
| 8 | `/app/ai/recommendations` | **Explicit** «Запустить анализ» — AI never auto-runs from onboarding |
| 9 | `/app/ai/recommendations/:id` | Explainability + usefulness feedback |
| 10 | `/app/support` | Tenant debug context for controlled production |

## Showcase scenarios

Documented in `docs/product/real_data_scenarios.md`:

- **A** First-time setup
- **B** Duplicate upload
- **C** Something is off (investigation)
- **D** AI decision workflow

## What to show vs hide in demos

**Show:**

- Analytics panel (`/app/analytics`), Upload, Reports, Processing status, Costs, AI recommendations (explicit launch)

**Hide (MVP mode default):**

- Raw ops JSON pages
- AI run raw objects
- Runtime enterprise control plane

Toggle via Settings → “Show internal operations pages” for technical audiences.

## Demo assets

| Asset | Location |
|-------|----------|
| Sample costs CSV | `docs/product/fixtures/sample_costs.csv` |
| Validation harness | `scripts/ux2_real_data_validation.py` |
| Scenario docs | `docs/product/real_data_scenarios.md` |
| Onboarding spec | `docs/product/onboarding.md` |

Replace placeholder report with a **sanitized real WB/Ozon export** for credible KPI story.

## Portfolio checklist

- [ ] Demo tenant created and onboarding complete (`ma.onboardingDone`)
- [ ] At least one **processed** report (visible on processing step)
- [ ] Dashboard shows KPIs at `/app/analytics`
- [ ] Costs imported (recommended for margin story)
- [ ] At least one AI recommendation via explicit «Запустить анализ» (optional)
- [ ] MVP mode enabled (internal ops hidden)

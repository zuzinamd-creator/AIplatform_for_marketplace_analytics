# Demo Environment (UX-3)

## Purpose

Prepare a **portfolio-ready demo** that shows real workflows without exposing internal operator tooling.

## Demo tenant setup

### 1) Create demo seller account

```bash
# Register via UI: /register
# Suggested credentials for demos (change in production):
# email: demo_seller@example.com
# password: demo_password_123
```

Or use validation script:

```bash
python scripts/ux2_real_data_validation.py \
  --email demo_seller@example.com \
  --password demo_password_123 \
  --report-file path/to/real_wb_export.csv \
  --costs-file docs/product/fixtures/sample_costs.csv \
  --run-ai
```

### 2) Enable demo mode

In the frontend:

- **Settings → Product mode → Demo**
- Or set `VITE_PRODUCT_MODE=demo` in `frontend/.env.local`

Demo mode shows a showcase path on the dashboard.

### 3) Complete onboarding

Navigate `/app/onboarding` and complete:

- Workspace name (e.g. “WB Seller Demo”)
- Marketplace selection
- First upload
- Cost import
- First AI analysis

## Demo walkthrough script (15 minutes)

| Step | Route | Talking point |
|------|-------|---------------|
| 1 | `/login` | Multi-tenant SaaS; each account is RLS-isolated |
| 2 | `/app/onboarding` | Progressive setup; minimal cognitive load |
| 3 | `/app/reports/upload` | Drag-drop; duplicate detection; governed ETL |
| 4 | `/app/reports` | Processing lifecycle visible to seller |
| 5 | `/app/status` | Plain-language trust; rebuild/queue transparency |
| 6 | `/app/costs` | Costs unlock profitability (future KPIs) |
| 7 | `/app/ai/recommendations` | Actionable AI with confidence |
| 8 | `/app/ai/recommendations/:id` | Explainability + usefulness feedback |
| 9 | `/app/support` | Tenant debug context for controlled production |

## Showcase scenarios

Documented in `docs/product/real_data_scenarios.md`:

- **A** First-time setup
- **B** Duplicate upload
- **C** Something is off (investigation)
- **D** AI decision workflow

## What to show vs hide in demos

**Show:**

- Dashboard, System status, Upload, Reports, Costs, AI recommendations

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

Replace placeholder report with a **sanitized real WB/Ozon export** for credible demos.

## Portfolio checklist

- [ ] Demo tenant created and onboarding complete
- [ ] At least one processed report
- [ ] Costs imported
- [ ] At least one AI recommendation with explainability
- [ ] System status shows “All clear” or explain active incident
- [ ] MVP mode enabled (internal ops hidden)

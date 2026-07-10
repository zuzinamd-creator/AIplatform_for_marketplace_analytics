# Pilot Trust Validation Program (Phase 9.7-A)

Seller validation for Cost Trust System across all three trust levels. Required before Analytics Hub physical merge (Phase 9.7-B).

**Baseline:** Production frontend `255bd2a` + Phase 9.7-A backend trust hardening.

---

## Program structure

| Parameter | Value |
|-----------|-------|
| Duration | 45–60 min per seller |
| Method | Moderated task-based validation |
| Environments | Production or staging with real seller data |
| Roles | Product PM (moderator), seller (participant) |

---

## Scenario A — INSUFFICIENT trust

**Profile:** 0% COGS coverage (e.g. MVP test tenant, new seller without cost upload)

### Tasks

| ID | Task | Expected behavior | Success criteria |
|----|------|-------------------|------------------|
| A1 | Open Dashboard | Global banner «Нет себестоимости»; profit = `—`; margin hidden | No numeric profit/margin |
| A2 | Open Comparison | Profit Δ = `н/д`; margin Δ = `н/д` | No false «profit declined» priority |
| A3 | Open Economics | SKU status = «Недостаточно данных» | No profitable/unprofitable labels |
| A4 | Open AI Recommendations | `CostTrustDisclosure` shows insufficient disclaimer | Seller understands limitation |
| A5 | Click COGS CTA from banner | Lands on `/app/costs` | CTA works from any page |
| A6 | View Dashboard profit chart | No profit line drawn | No null→0 chart artifact |

**Pass threshold:** 6/6 tasks; zero false profit/margin/delta display.

**Production status:** API + bundle validated (9.6B-3). Browser walkthrough pending.

---

## Scenario B — PARTIAL trust

**Profile:** 1–99% COGS coverage (pilot seller with partial cost upload)

### Tasks

| ID | Task | Expected behavior | Success criteria |
|----|------|-------------------|------------------|
| B1 | Open Dashboard | Banner warns; profit = `~₽`; margin = `—`; chart dashed | Seller sees estimate |
| B2 | Open Comparison | Profit Δ with warn tone; margin Δ = `н/д`; partial priority warning | No strong profit-decline conclusion |
| B3 | Open Economics | SKU with COGS: «Оценка: …»; margin column hidden; compare Δ only when B-period exists | No `?? 0` false deltas |
| B4 | Open SKU Drilldown | Profit ~formatted; margin hidden; compare deltas approximate or absent | No false precision |
| B5 | Open AI Recommendations | Disclosure: «оценочная», margin hidden note | Seller understands limitation |
| B6 | Upload COGS for 1 missing SKU | Coverage bar updates on Cost Coverage page | Progress visible |

**Pass threshold:** 6/6 tasks; seller articulates «profit is approximate».

**Production status:** Unit-tested; live pilot required.

---

## Scenario C — FULL trust

**Profile:** 100% COGS coverage (pilot seller with complete cost upload for all sold SKUs)

### Tasks

| ID | Task | Expected behavior | Success criteria |
|----|------|-------------------|------------------|
| C1 | Open Dashboard | Badge «Проверено»; exact profit/margin; no banner; solid chart | Full trust UX |
| C2 | Open Comparison | Exact profit/margin deltas; profit-decline priority when Δ < 0 | Actionable insights |
| C3 | Open Economics | Прибыльный/Убыточный labels; margin visible; compare Δ exact | SKU classification reliable |
| C4 | Open Reconciliation | Profit KPI with «Проверено» badge | Trust on finance surface |
| C5 | Open AI Recommendations | Disclosure: «проверенная прибыль» | Recommendations trusted |
| C6 | Compare Dashboard vs Comparison | Dashboard = overview; Comparison = full period deltas | Clear hierarchy |

**Pass threshold:** 6/6 tasks; seller trusts profit for decisions.

**Production status:** Unit-tested; live pilot required.

---

## API validation (all scenarios)

| Endpoint | Check |
|----------|-------|
| `GET /analytics/kpis/period-compare` | `delta_profit: null` when either period `total_profit` is null |
| `GET /analytics/kpis/summary` | `total_profit` gated per `profit_metrics_trust` |
| `GET /analytics/cost-coverage` | Coverage % matches trust classification |

---

## Exit criteria for Phase 9.7-B (Analytics Hub)

1. All three scenarios pass with live pilot sellers
2. Zero false profit delta artifacts in moderated sessions
3. Backend `delta_profit` null contract verified in production API
4. Product sign-off documented in release certification

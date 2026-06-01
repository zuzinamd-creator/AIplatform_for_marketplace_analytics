# Real Seller Scenarios (PRODUCT-VALIDATION)

Realistic marketplace seller profiles for product validation. Each profile describes **expected KPI patterns**, **AI behavior**, and **UX expectations**.

> Data source: real Wildberries/Ozon exports (sanitized) preferred. Small fixtures in `docs/product/fixtures/` exercise upload lifecycle only — replace with real exports for meaningful KPI/AI validation.

---

## Seller profile catalog

| Profile | Business shape | Expected KPI signals | Primary seller question |
|---------|----------------|----------------------|-------------------------|
| **Healthy seller** | Stable revenue, positive margin | Flat/up trend, balanced top SKUs | “Anything I should optimize?” |
| **Declining seller** | Revenue down 15–30% | Negative period delta, margin stable or falling | “What changed vs last period?” |
| **Inventory chaos** | Frequent stock mismatches | High discrepancy cost, drift/anomalies | “Which SKUs/warehouses are wrong?” |
| **High-return products** | Returns erode profit | Revenue ok, profit down, low margin SKUs | “Which products lose money after returns?” |
| **Warehouse imbalance** | Stock concentrated wrong | One WH high discrepancy, others normal | “Where should I rebalance stock?” |
| **Stale inventory** | Old stock, low turnover | Flat sales, high snapshot age | “What is not selling?” |
| **Margin collapse** | Costs up or prices down | Revenue flat, margin_pct sharply down | “Why is profit disappearing?” |
| **Seasonal spike** | Short demand burst | Sharp trend peak, ABC skew to few SKUs | “Did spike SKUs sustain or fade?” |

---

## Profile details

### 1) Healthy seller

- **Upload:** weekly sales + stock reports
- **Dashboard:** revenue/profit stable; no stale badge
- **AI:** 1–2 optimization hints (pricing, restock), not alarms
- **Pass:** seller completes daily routine in &lt; 10 min without support

### 2) Declining seller

- **KPI:** `period-compare` shows negative `delta_revenue` / `delta_profit`
- **Dashboard:** trend chart downward
- **AI:** should prioritize root-cause (SKU mix, returns, ads) with evidence
- **Fail pattern:** generic “optimize marketing” without SKU linkage

### 3) Inventory chaos

- **Ops:** anomalies + drift checks populated
- **Analytics:** `inventory-risk.discrepancy_cost_total` elevated
- **AI:** warehouse/SKU-specific recommendations
- **Pass:** seller can name affected warehouse from product UI (today: partial — API/script only)

### 4) High-return products

- **KPI:** top SKUs by revenue ≠ top by profit
- **Costs:** cost import required for accurate margin
- **AI:** flag SKUs with margin collapse
- **Gap:** no dedicated “returns impact” KPI widget yet

### 5) Warehouse imbalance

- **Analytics:** `GET /analytics/kpis/warehouses` shows one outlier WH
- **Seller action:** transfer/restock (external to platform)
- **UX gap:** no warehouse chart in frontend

### 6) Stale inventory

- **Signal:** low units_sold on many SKUs; old `data_as_of` if reports not uploaded
- **AI:** should not urge “immediate action” when `stale_data_warning=true`
- **Pass:** confidence penalized (AI-USEFULNESS quality engine)

### 7) Margin collapse

- **KPI:** margin_pct drops period-over-period while revenue flat
- **Requires:** costs imported (`/app/costs`)
- **AI:** margin-focused recommendation with evidence
- **Onboarding gap:** costs step easy to skip

### 8) Seasonal spike

- **Trend:** single-week revenue peak in chart
- **ABC:** A-bucket concentrates on spike SKUs
- **Weekly workflow:** compare spike week vs following week via period-compare

---

## Validation matrix

For each profile, validate:

| Dimension | Question |
|-----------|----------|
| Dashboard usefulness | Can seller answer profile’s primary question from dashboard alone? |
| AI usefulness | Are recommendations specific, evidence-linked, actionable? |
| Operational UX | Can seller distinguish processing delay vs error vs stale data? |
| Anomaly clarity | Are anomalies understandable without JSON inspection? |

---

## Recommended demo sequence

1. **Healthy seller** — show happy path (onboarding → upload → dashboard → AI feedback)
2. **Declining seller** — show period comparison via script/API
3. **Stale inventory** — show trust banners + reduced AI confidence
4. **Inventory chaos** — show incident workflow on System Status

Script:

```bash
python scripts/product_validation_simulation.py --workflow all --marketplace wildberries
```

With real data:

```bash
python scripts/product_validation_simulation.py --workflow daily \
  --report-file /path/to/wb_sales_export.csv --run-ai
```

---

## Fixture limitations

| File | Purpose | Limitation |
|------|---------|------------|
| `sample_costs.csv` | Cost import smoke test | Not tied to real SKUs |
| `sample_report_placeholder.csv` | Upload lifecycle | Will not produce rich aggregates |

For portfolio demos, use **one real sanitized export** per marketplace to populate KPIs credibly.

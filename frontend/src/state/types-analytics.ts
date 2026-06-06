export type AnalyticsFreshnessMeta = {
  semantics_version: string;
  data_as_of?: string | null;
  rebuild_running: number;
  rebuild_pending: number;
  queue_processing: number;
  queue_pending: number;
  dead_letters: number;
  stale_data_warning: boolean;
  degraded_mode: boolean;
  generated_at: string;
};

export type IntegrityWarning = {
  code: string;
  severity: "info" | "warning" | "critical" | string;
  message: string;
  context?: Record<string, string> | null;
};

export type AnalyticsIntegrityMeta = {
  warnings: IntegrityWarning[];
  financial_completeness_score?: string | null;
  sku_cost_coverage_pct?: string | null;
  profit_metrics_trust?: "full" | "partial" | "insufficient" | string | null;
};

export type RevenueKpiSummaryResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  kpis: {
    total_revenue: string;
    total_profit: string | null;
    margin_pct?: string | null;
    units_sold: number;
    average_check?: string | null;
  };
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type RevenueTrendResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  points: Array<{
    date: string;
    revenue: string;
    net_profit: string;
    margin_pct?: string | null;
    units_sold: number;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type TopSkusResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  sort: string;
  items: Array<{
    sku: string;
    revenue: string;
    net_profit: string;
    margin_pct?: string | null;
    units_sold: number;
    contribution_pct?: string | null;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type AnalyticsCoverageResponse = {
  marketplaces: string[];
  available_min_date?: string | null;
  available_max_date?: string | null;
  available_by_marketplace: Record<string, { min_date?: string | null; max_date?: string | null }>;
  uploaded_report_types: Array<{ marketplace: string; report_type: string; count: number }>;
  missing_periods: Array<{ start: string; end: string; missing_days: number }>;
  recommendations: Array<{ code: string; title: string; message: string; severity: string }>;
  financial_completeness_score?: string | null;
  freshness: AnalyticsFreshnessMeta;
  warnings: IntegrityWarning[];
};

export type FinancialKpiSummaryResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  kpis: {
    sales_revenue: string;
    returns_amount: string;
    payout: string;
    commission: string;
    logistics: string;
    storage_fee: string;
    acquiring: string;
    advertisement: string;
    penalties: string;
    deductions: string;
    compensation: string;
    gross_profit: string;
    margin_pct?: string | null;
    return_rate_pct?: string | null;
    total_to_pay: string;
  };
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type FinancialTrendsResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  points: Array<{
    date: string;
    sales_revenue: string;
    gross_profit: string;
    margin_pct?: string | null;
    logistics: string;
    advertisement: string;
    payout: string;
    returns_amount: string;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type SkuEconomicsResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  total: number;
  items: Array<{
    sku: string;
    revenue: string;
    contribution_margin: string;
    gross_profit: string;
    cogs: string;
    returns_amount: string;
    payout: string;
    commissions: string;
    logistics: string;
    storage: string;
    ads: string;
    penalties: string;
    margin_pct?: string | null;
    return_rate?: string | null;
    ad_cost_ratio?: string | null;
    logistics_burden?: string | null;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type CostCoverageResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  total_skus: number;
  covered_skus: number;
  sku_cost_coverage_pct?: string | null;
  cost_completeness_score?: string | null;
  items: Array<{
    sku: string;
    units_sold: number;
    revenue: string;
    cogs: string;
    cost_coverage_pct?: string | null;
    last_cost_effective_from?: string | null;
    warnings: IntegrityWarning[];
  }>;
  missing_skus?: string[];
  freshness: AnalyticsFreshnessMeta;
  warnings: IntegrityWarning[];
};

export type ReconciliationResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  breakdown: {
    revenue: string;
    returns_amount: string;
    commissions: string;
    logistics: string;
    storage: string;
    ads: string;
    penalties: string;
    acquiring: string;
    deductions: string;
    compensation: string;
    cogs: string;
    expected_payout: string;
    actual_payout: string;
    payout_difference: string;
    profit: string;
    payout_is_not_profit_explanation: string;
  };
  freshness: AnalyticsFreshnessMeta;
  warnings: IntegrityWarning[];
};

export type InventoryEconomicsResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  snapshot_date?: string | null;
  total_skus: number;
  items: Array<{
    sku: string;
    stock_units: number;
    sold_units: number;
    avg_stock_units?: string | null;
    turnover_ratio?: string | null;
    turnover_days?: string | null;
    frozen_capital?: string | null;
    unit_cost?: string | null;
    days_since_last_sale?: number | null;
    stock_risk?: "ok" | "stockout" | "overstock" | string | null;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type InventorySlowMoversResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  snapshot_date?: string | null;
  threshold_days: number;
  items: Array<{
    sku: string;
    stock_units: number;
    frozen_capital?: string | null;
    unit_cost?: string | null;
    days_since_last_sale: number;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type InventoryDeadStockResponse = {
  marketplace: string;
  period_start: string;
  period_end: string;
  snapshot_date?: string | null;
  threshold_days: number;
  items: Array<{
    sku: string;
    stock_units: number;
    frozen_capital?: string | null;
    unit_cost?: string | null;
    days_since_last_sale: number;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};

export type SkuDrilldownResponse = {
  marketplace: string;
  sku: string;
  period_start: string;
  period_end: string;
  points: Array<{
    date: string;
    revenue: string;
    gross_profit: string;
    contribution_margin: string;
    margin_pct?: string | null;
    returns_amount: string;
    logistics: string;
    ads: string;
    penalties: string;
    payout: string;
    stock_units?: number | null;
  }>;
  freshness: AnalyticsFreshnessMeta;
  integrity?: AnalyticsIntegrityMeta | null;
};


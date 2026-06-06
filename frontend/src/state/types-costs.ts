export type CostCreateRequest = {
  internal_sku: string;
  effective_from: string;
  product_cost: string;
  packaging_cost?: string | null;
  inbound_logistics_cost?: string | null;
  additional_cost?: string | null;
  currency: string;
  comment?: string | null;
};

export type CostResponse = {
  id: string;
  internal_sku: string;
  effective_from: string;
  product_cost: string;
  packaging_cost?: string | null;
  inbound_logistics_cost?: string | null;
  additional_cost?: string | null;
  cost: string;
  currency: string;
  comment?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type CostUpdateRequest = {
  product_cost?: string;
  packaging_cost?: string;
  inbound_logistics_cost?: string;
  additional_cost?: string;
  currency?: string;
  comment?: string | null;
};

export type CostListParams = {
  sku?: string;
  as_of?: string;
  effective_from?: string;
  effective_to?: string;
};

export type SalesCostCoverageGapsResponse = {
  marketplace: string;
  period_start: string | null;
  period_end: string | null;
  total_selling_skus: number;
  covered_skus: number;
  sku_cost_coverage_pct?: string | null;
  missing_skus: string[];
};

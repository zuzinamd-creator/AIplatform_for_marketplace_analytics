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
  currency: string;
  comment?: string | null;
  created_at: string;
  updated_at: string;
};


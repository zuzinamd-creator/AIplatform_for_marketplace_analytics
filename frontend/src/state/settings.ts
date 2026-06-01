export type ProductMode = "mvp" | "demo" | "full";

export type TenantSettings = {
  product_mode: ProductMode;
  local_only_mode: boolean;
  show_internal_ops: boolean;
  email_notifications: boolean;
  stale_data_alerts: boolean;
  ai_degraded_alerts: boolean;
  rebuild_alerts: boolean;
};

const KEY = "ma.tenantSettings";

const defaults: TenantSettings = {
  product_mode: (import.meta.env.VITE_PRODUCT_MODE as ProductMode) ?? "mvp",
  local_only_mode: (import.meta.env.VITE_LOCAL_ONLY_MODE ?? "true") === "true",
  show_internal_ops: false,
  email_notifications: false,
  stale_data_alerts: true,
  ai_degraded_alerts: true,
  rebuild_alerts: true,
};

export function loadSettings(): TenantSettings {
  const raw = localStorage.getItem(KEY);
  if (!raw) return { ...defaults };
  try {
    return { ...defaults, ...(JSON.parse(raw) as Partial<TenantSettings>) };
  } catch {
    return { ...defaults };
  }
}

export function saveSettings(s: TenantSettings) {
  localStorage.setItem(KEY, JSON.stringify(s));
}

export function isMvpMode() {
  const s = loadSettings();
  return s.product_mode === "mvp" && !s.show_internal_ops;
}

export function isDemoMode() {
  return loadSettings().product_mode === "demo";
}

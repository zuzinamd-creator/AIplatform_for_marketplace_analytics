/** Frontend feature flags for phased rollout (Phase 9.6B+). */
export const FEATURE_FLAGS = {
  /** When true, AppShell mounts the global CostTrustBanner with live integrity data. */
  costTrustBannerGlobal: true,
  /** When true, /app/analytics renders tab shell with embedded analytics pages (Phase 9.8-A). */
  analyticsHubTabs: true,
} as const;

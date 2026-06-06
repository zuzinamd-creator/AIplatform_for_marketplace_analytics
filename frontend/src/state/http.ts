import axios from "axios";

import { handleUnauthorized } from "./session";

import type {
  AIOperationalStatusResponse,
  AIRunDetailResponse,
  AIExecutionResultResponse,
  PaginatedAIRunsResponse,
  PaginatedAIInsightsResponse,
  PaginatedRecommendationsResponse,
  IntelligenceRunCreateRequest,
  IntelligenceRunResponse,
  RecommendationFeedbackRequest,
  RecommendationResponse,
  ExplainabilityResponse,
  RecommendationStatsResponse,
  AIDigestResponse,
  TodaysFocusResponse,
  UsefulnessMetricsResponse,
  ConversationReplyResponse,
} from "./types-ai";

export type AICostsResponse = {
  runs_total: number;
  estimated_cost_usd: number;
  daily_cap_usd: number;
  daily_spend_usd: number;
  daily_cap_remaining_usd: number;
  per_run_cap_usd: number;
  by_workflow: Array<Record<string, unknown>>;
  by_prompt: Array<Record<string, unknown>>;
  by_provider: Array<Record<string, unknown>>;
  expensive_runs: Array<Record<string, unknown>>;
  repeated_prompts: Array<Record<string, unknown>>;
  generated_at: string;
};

export type AIProviderStatusResponse = {
  primary_provider: string;
  failover_provider?: string | null;
  circuit_breaker_open: boolean;
  streaming_enabled: boolean;
  cost_tracking_enabled: boolean;
  prompt_runtime_version: string;
  providers: Array<Record<string, unknown>>;
  estimated_monthly_cost_usd?: number | null;
};
export type CostImportIssue = {
  severity: string;
  code: string;
  message: string;
  row_index?: number | null;
};

export type CostImportPreviewRow = {
  row_index: number;
  internal_sku?: string | null;
  effective_from?: string | null;
  product_cost?: string | null;
  packaging_cost?: string | null;
  inbound_logistics_cost?: string | null;
  additional_cost?: string | null;
  currency?: string | null;
  comment?: string | null;
  total_cost?: string | null;
};

export type CostImportPreviewResponse = {
  detected_columns: Record<string, string | null>;
  total_rows: number;
  preview_rows: CostImportPreviewRow[];
  issues: CostImportIssue[];
};

export type CostImportResultResponse = {
  detected_columns: Record<string, string | null>;
  total_rows: number;
  imported_rows: number;
  skipped_rows: number;
  imported_distinct_skus: number;
  invalid_sku_count: number;
  issues: CostImportIssue[];
};
import type { Token, UserCreate, UserResponse } from "./types-auth";
import type {
  CostCreateRequest,
  CostListParams,
  CostResponse,
  CostUpdateRequest,
  SalesCostCoverageGapsResponse,
} from "./types-costs";
import type { ReportResponse, ReportUploadResponse } from "./types-reports";
import type { WorkflowEventCreateRequest, WorkflowEventResponse, WorkflowHistoryResponse } from "./types-workflow";
import type {
  AnalyticsCoverageResponse,
  CostCoverageResponse,
  FinancialKpiSummaryResponse,
  FinancialTrendsResponse,
  InventoryDeadStockResponse,
  InventoryEconomicsResponse,
  InventorySlowMoversResponse,
  ReconciliationResponse,
  RevenueKpiSummaryResponse,
  RevenueTrendResponse,
  SkuEconomicsResponse,
  SkuDrilldownResponse,
  TopSkusResponse,
} from "./types-analytics";
import type {
  PaginatedAnomaliesResponse,
  PaginatedDriftChecksResponse,
  PaginatedQueueResponse,
  PaginatedRebuildsResponse,
  RuntimeHealthResponse,
  RuntimeSummaryResponse,
  SemanticsStatusOpsResponse,
} from "./types-ops";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? "/api/v1";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export const http = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30_000,
});

http.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

const AUTH_PUBLIC_PATHS = ["/auth/login", "/auth/register", "/auth/forgot-password", "/auth/reset-password"];

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const url = error.config?.url ?? "";
      const isPublicAuth = AUTH_PUBLIC_PATHS.some((path) => url.includes(path));
      if (!isPublicAuth && accessToken) {
        handleUnauthorized();
      }
    }
    return Promise.reject(error);
  },
);

function unwrap<T>(data: unknown): T {
  return data as T;
}

export function formatApiError(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data as { detail?: unknown } | undefined;
    if (typeof detail?.detail === "string") return detail.detail;
    if (Array.isArray(detail?.detail)) {
      return detail.detail
        .map((item) => {
          if (typeof item === "object" && item && "msg" in item) {
            return String((item as { msg: string }).msg);
          }
          return String(item);
        })
        .join("; ");
    }
    if (err.response?.status === 401) return "Неверный email или пароль.";
    if (err.response?.status === 422) return "Проверьте формат email и пароль (минимум 8 символов).";
    if (err.response?.status === 503) {
      return "Отправка email недоступна. Обратитесь к администратору.";
    }
    if (err.code === "ECONNABORTED" || err.message.toLowerCase().includes("timeout")) {
      return "Операция заняла слишком много времени. Проверьте список отчётов — удаление могло завершиться на сервере.";
    }
    if (err.response?.status === 500) {
      return "Server error — try again or check docker compose logs api";
    }
    if (err.code === "ECONNABORTED") {
      return "Request timed out — large reports may need more time; retry upload.";
    }
    if (err.code === "ERR_NETWORK") {
      return "Network error — is the API running at " + API_BASE_URL + "?";
    }
  }
  return err instanceof Error ? err.message : "Request failed";
}

export const api = {
  auth: {
    async register(payload: UserCreate) {
      const { data } = await http.post("/auth/register", payload);
      return unwrap<UserResponse>(data);
    },
    async login(username: string, password: string) {
      const body = new URLSearchParams();
      body.set("username", username);
      body.set("password", password);
      const { data } = await http.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      return unwrap<Token>(data);
    },
    async me() {
      const { data } = await http.get("/auth/me");
      return unwrap<UserResponse>(data);
    },
    async forgotPassword(email: string) {
      const { data } = await http.post("/auth/forgot-password", { email });
      return unwrap<{ message: string }>(data);
    },
    async changePassword(payload: {
      current_password: string;
      new_password: string;
      confirm_password: string;
    }) {
      const { data } = await http.post("/auth/change-password", payload);
      return unwrap<{ message: string }>(data);
    },
    async resetPassword(payload: { token: string; new_password: string; confirm_password: string }) {
      const { data } = await http.post("/auth/reset-password", payload);
      return unwrap<Token>(data);
    },
  },

  reports: {
    async list(skip = 0, limit = 200) {
      const { data } = await http.get("/reports", { params: { skip, limit } });
      return unwrap<ReportResponse[]>(data);
    },
    async get(reportId: string) {
      const { data } = await http.get(`/reports/${reportId}`);
      return unwrap<ReportResponse>(data);
    },
    async retry(reportId: string) {
      const { data } = await http.post(`/reports/${reportId}/retry`);
      return unwrap<ReportResponse>(data);
    },
    async delete(reportId: string) {
      await http.delete(`/reports/${reportId}`, { timeout: 180_000 });
    },
    async upload(
      form: FormData,
      onProgress?: (pct: number, loaded: number, total?: number) => void,
    ) {
      const { data } = await http.post("/reports/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300_000,
        onUploadProgress: (evt) => {
          if (!onProgress) return;
          const total = evt.total ?? undefined;
          const loaded = evt.loaded ?? 0;
          const pct = total ? Math.round((loaded / total) * 100) : 0;
          onProgress(pct, loaded, total);
        },
      });
      return unwrap<ReportUploadResponse>(data);
    },
  },

  costs: {
    async create(payload: CostCreateRequest) {
      const { data } = await http.post("/costs", payload);
      return unwrap<CostResponse>(data);
    },
    async list(params?: CostListParams) {
      const { data } = await http.get("/costs", { params: params ?? {} });
      return unwrap<CostResponse[]>(data);
    },
    async update(costId: string, payload: CostUpdateRequest) {
      const { data } = await http.patch(`/costs/${costId}`, payload);
      return unwrap<CostResponse>(data);
    },
    async delete(costId: string) {
      await http.delete(`/costs/${costId}`);
    },
    async import(file: File) {
      const form = new FormData();
      form.set("file", file);
      const { data } = await http.post("/costs/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return unwrap<CostResponse[]>(data);
    },
    async previewImport(file: File) {
      const form = new FormData();
      form.set("file", file);
      const { data } = await http.post("/costs/import/preview", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      return unwrap<CostImportPreviewResponse>(data);
    },
    async importV2(file: File) {
      const form = new FormData();
      form.set("file", file);
      const { data } = await http.post("/costs/import/v2", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300_000,
      });
      return unwrap<CostImportResultResponse>(data);
    },
    async downloadImportTemplate(): Promise<void> {
      const { data } = await http.get<Blob>("/costs/import/template", {
        responseType: "blob",
      });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Шаблон Себестоимости.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    },
    async templateInfo() {
      const { data } = await http.get("/costs/import/template-info");
      return unwrap<Record<string, unknown>>(data);
    },
    async get(costId: string) {
      const { data } = await http.get(`/costs/${costId}`);
      return unwrap<CostResponse>(data);
    },
    async salesCoverageGaps(params: { marketplace: string; start?: string; end?: string; limit?: number }) {
      const { data } = await http.get("/costs/sales-coverage-gaps", { params });
      return unwrap<SalesCostCoverageGapsResponse>(data);
    },
  },

  ops: {
    async queue(skip = 0, limit = 50) {
      const { data } = await http.get("/ops/queue", { params: { skip, limit } });
      return unwrap<PaginatedQueueResponse>(data);
    },
    async deadLetters(skip = 0, limit = 50) {
      const { data } = await http.get("/ops/dead-letters", { params: { skip, limit } });
      return unwrap<PaginatedQueueResponse>(data);
    },
    async rebuilds(skip = 0, limit = 50, status?: string) {
      const { data } = await http.get("/ops/rebuilds", { params: { skip, limit, status } });
      return unwrap<PaginatedRebuildsResponse>(data);
    },
    async driftChecks(skip = 0, limit = 50, consistentOnly?: boolean) {
      const { data } = await http.get("/ops/drift-checks", {
        params: { skip, limit, consistent_only: consistentOnly },
      });
      return unwrap<PaginatedDriftChecksResponse>(data);
    },
    async anomalies(skip = 0, limit = 50) {
      const { data } = await http.get("/ops/anomalies", { params: { skip, limit } });
      return unwrap<PaginatedAnomaliesResponse>(data);
    },
    async runtimeHealth() {
      const { data } = await http.get("/ops/runtime/health");
      return unwrap<RuntimeHealthResponse>(data);
    },
    async runtimeSummary() {
      const { data } = await http.get("/ops/runtime/summary");
      return unwrap<RuntimeSummaryResponse>(data);
    },
    async semanticsStatus() {
      const { data } = await http.get("/ops/semantics-status");
      return unwrap<SemanticsStatusOpsResponse>(data);
    },
  },
  system: {
    async persistenceStatus() {
      const { data } = await http.get("/system/persistence-status");
      return unwrap<Record<string, unknown>>(data);
    },
    async dataIntegrity() {
      const { data } = await http.get("/system/data-integrity");
      return unwrap<Record<string, unknown>>(data);
    },
  },

  ai: {
    async createRun(body: { workflow: string; prompt_id: string; semantics_version?: string; session_id?: string | null; report_id?: string | null; }) {
      const { data } = await http.post("/ai/runs", body);
      return unwrap<AIExecutionResultResponse>(data);
    },
    async runIntelligence(body: IntelligenceRunCreateRequest) {
      const { data } = await http.post("/ai/intelligence/runs", body);
      return unwrap<IntelligenceRunResponse>(data);
    },
    async runIntelligenceForPeriod(body: {
      workflow: string;
      prompt_id: string;
      semantics_version?: string;
      marketplace: string;
      period_start: string;
      period_end: string;
    }) {
      const { data } = await http.post("/ai/intelligence/period-runs", body);
      return unwrap<IntelligenceRunResponse>(data);
    },
    async runs(skip = 0, limit = 50) {
      const { data } = await http.get("/ai/runs", { params: { skip, limit } });
      return unwrap<PaginatedAIRunsResponse>(data);
    },
    async run(runId: string) {
      const { data } = await http.get(`/ai/runs/${runId}`);
      return unwrap<AIRunDetailResponse>(data);
    },
    async insights(skip = 0, limit = 50, workflow?: string) {
      const { data } = await http.get("/ai/insights", { params: { skip, limit, workflow } });
      return unwrap<PaginatedAIInsightsResponse>(data);
    },
    async recommendations(skip = 0, limit = 50, opts?: { seller_state?: string; group?: string }) {
      const { data } = await http.get("/ai/recommendations", {
        params: { skip, limit, seller_state: opts?.seller_state, group: opts?.group },
      });
      return unwrap<PaginatedRecommendationsResponse>(data);
    },
    async recommendation(recommendationId: string) {
      const { data } = await http.get(`/ai/recommendations/${recommendationId}`);
      return unwrap<RecommendationResponse>(data);
    },
    async explainability(recommendationId: string) {
      const { data } = await http.get(`/ai/recommendations/${recommendationId}/explainability`);
      return unwrap<ExplainabilityResponse>(data);
    },
    async recommendationStats() {
      const { data } = await http.get("/ai/recommendations/stats");
      return unwrap<RecommendationStatsResponse>(data);
    },
    async operationalStatus() {
      const { data } = await http.get("/ai/operational/status");
      return unwrap<AIOperationalStatusResponse>(data);
    },
    async feedback(recommendationId: string, body: RecommendationFeedbackRequest) {
      const { data } = await http.post(`/ai/recommendations/${recommendationId}/feedback`, body);
      return unwrap<{ status: string }>(data);
    },
    async workflow(recommendationId: string, body: { action: string; snooze_days?: number }) {
      const { data } = await http.patch(`/ai/recommendations/${recommendationId}/workflow`, body);
      return unwrap<RecommendationResponse>(data);
    },
    async ask(recommendationId: string, question: string) {
      const { data } = await http.post(`/ai/recommendations/${recommendationId}/ask`, { question });
      return unwrap<ConversationReplyResponse>(data);
    },
    async digest(digestType: "daily" | "weekly" | "anomaly") {
      const { data } = await http.get(`/ai/digests/${digestType}`);
      return unwrap<AIDigestResponse>(data);
    },
    async todaysFocus() {
      const { data } = await http.get("/ai/todays-focus");
      return unwrap<TodaysFocusResponse>(data);
    },
    async usefulnessMetrics() {
      const { data } = await http.get("/ai/usefulness/metrics");
      return unwrap<UsefulnessMetricsResponse>(data);
    },
    async costs() {
      const { data } = await http.get("/ai/costs");
      return unwrap<AICostsResponse>(data);
    },
    async providerStatus() {
      const { data } = await http.get("/ai/providers/status");
      return unwrap<AIProviderStatusResponse>(data);
    },
    async usage() {
      const { data } = await http.get("/ai/usage");
      return unwrap<{ tokens_total: number; estimated_cost_usd?: number; runs_total: number }>(data);
    },
  },

  dashboard: {
    async summary(params: {
      marketplace: string;
      start: string;
      end: string;
      compare_start?: string;
      compare_end?: string;
    }) {
      const { data } = await http.get("/dashboard/summary", { params });
      return unwrap<{
        queue: PaginatedQueueResponse;
        runtime: RuntimeSummaryResponse;
        ai_ops: AIOperationalStatusResponse;
        todays_focus: TodaysFocusResponse;
        recommendations: PaginatedRecommendationsResponse;
        revenue_summary: RevenueKpiSummaryResponse;
        revenue_summary_compare: RevenueKpiSummaryResponse | null;
        revenue_trend_daily: RevenueTrendResponse;
        finance_summary: FinancialKpiSummaryResponse;
        finance_trend_daily: FinancialTrendsResponse;
        top_skus: TopSkusResponse;
        coverage: AnalyticsCoverageResponse;
        cost_coverage: CostCoverageResponse | null;
        generated_at: string;
      }>(data);
    },
  },

  analytics: {
    async revenueSummary(params: { marketplace: string; start: string; end: string }) {
      const { data } = await http.get("/analytics/kpis/summary", { params });
      return unwrap<RevenueKpiSummaryResponse>(data);
    },
    async revenueTrendDaily(params: { marketplace: string; start: string; end: string }) {
      const { data } = await http.get("/analytics/kpis/trends/daily", { params });
      return unwrap<RevenueTrendResponse>(data);
    },
    async topSkus(params: { marketplace: string; start: string; end: string; limit?: number; sort?: string }) {
      const { data } = await http.get("/analytics/kpis/top-skus", { params });
      return unwrap<TopSkusResponse>(data);
    },
    async coverage(params?: { semantics_version?: string }) {
      const { data } = await http.get("/analytics/coverage", { params });
      return unwrap<AnalyticsCoverageResponse>(data);
    },
    async financialSummary(params: { marketplace: string; start: string; end: string }) {
      const { data } = await http.get("/analytics/kpis/finance/summary", { params });
      return unwrap<FinancialKpiSummaryResponse>(data);
    },
    async financialTrendDaily(params: { marketplace: string; start: string; end: string }) {
      const { data } = await http.get("/analytics/kpis/finance/trends/daily", { params });
      return unwrap<FinancialTrendsResponse>(data);
    },
    async costCoverage(params: { marketplace: string; start: string; end: string; limit?: number; q?: string }) {
      const { data } = await http.get("/analytics/cost-coverage", { params });
      return unwrap<CostCoverageResponse>(data);
    },
    async reconciliationPeriod(params: { marketplace: string; start: string; end: string }) {
      const { data } = await http.get("/analytics/reconciliation/period", { params });
      return unwrap<ReconciliationResponse>(data);
    },
    async skuEconomics(params: {
      marketplace: string;
      start: string;
      end: string;
      skip?: number;
      limit?: number;
      sort?: string;
      order?: string;
      q?: string;
    }) {
      const { data } = await http.get("/analytics/sku-economics", { params });
      return unwrap<SkuEconomicsResponse>(data);
    },
    async inventoryEconomics(params: {
      marketplace: string;
      start: string;
      end: string;
      limit?: number;
      q?: string;
      semantics_version?: string;
    }) {
      const { data } = await http.get("/analytics/inventory-economics", { params });
      return unwrap<InventoryEconomicsResponse>(data);
    },
    async inventorySlowMovers(params: {
      marketplace: string;
      start: string;
      end: string;
      threshold_days?: number;
      limit?: number;
      semantics_version?: string;
    }) {
      const { data } = await http.get("/analytics/inventory-economics/slow-movers", { params });
      return unwrap<InventorySlowMoversResponse>(data);
    },
    async inventoryDeadStock(params: {
      marketplace: string;
      start: string;
      end: string;
      threshold_days?: number;
      limit?: number;
      semantics_version?: string;
    }) {
      const { data } = await http.get("/analytics/inventory-economics/dead-stock", { params });
      return unwrap<InventoryDeadStockResponse>(data);
    },
    async skuDrilldown(params: {
      marketplace: string;
      start: string;
      end: string;
      semantics_version?: string;
      sku: string;
    }) {
      const { sku, ...rest } = params;
      const { data } = await http.get(`/analytics/sku-economics/sku/${encodeURIComponent(sku)}/drilldown`, {
        params: rest,
      });
      return unwrap<SkuDrilldownResponse>(data);
    },
  },

  workflow: {
    async createEvent(body: WorkflowEventCreateRequest) {
      const { data } = await http.post("/workflow/events", body);
      return unwrap<WorkflowEventResponse>(data);
    },
    async history(params?: { recommendation_id?: string; limit?: number }) {
      const { data } = await http.get("/workflow/history", { params });
      return unwrap<WorkflowHistoryResponse>(data);
    },
    async dueReminders(params?: { limit?: number }) {
      const { data } = await http.get("/workflow/reminders/due", { params });
      return unwrap<WorkflowEventResponse[]>(data);
    },
  },
};


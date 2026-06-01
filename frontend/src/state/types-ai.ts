export type PageMeta = {
  total: number;
  skip: number;
  limit: number;
};

export type PaginatedAIRunsResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
};

export type AIRunDetailResponse = Record<string, unknown>;

export type AIExecutionResultResponse = {
  run: Record<string, unknown>;
  insight_id?: string | null;
  confidence: string | number;
  degraded_mode: boolean;
  stale_data_warning: boolean;
  summary: string;
};

export type PaginatedAIInsightsResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
};

export type PaginatedRecommendationsResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
};

export type RecommendationResponse = Record<string, unknown>;

export type RecommendationStatsResponse = {
  total: number;
  ignored_7d: number;
  avg_rating?: number | null;
  helpful_rate?: number | null;
  accept_rate?: number | null;
  reject_rate?: number | null;
  fatigue_top_fingerprints?: Array<{ fingerprint: string; count: number }>;
  action_conversion_rate?: number | null;
  completed_count?: number;
  dismissed_count?: number;
};

export type SellerUsefulnessView = {
  why_this_matters?: string;
  expected_business_impact?: string;
  urgency?: string;
  urgency_score?: number;
  estimated_upside?: string;
  estimated_downside?: string;
  concrete_next_action?: string;
  confidence_explanation?: string;
  limitations?: string[];
};

export type AIDigestResponse = {
  digest_type: string;
  generated_at: string;
  headline: string;
  sections: Array<{ title: string; body: string; priority: string }>;
  active_recommendation_count: number;
  advisory_notice: string;
};

export type UsefulnessMetricsResponse = {
  total_recommendations: number;
  accepted_count: number;
  rejected_count: number;
  ignored_count: number;
  completed_count: number;
  dismissed_count: number;
  saved_count: number;
  snoozed_count: number;
  repeated_fingerprint_count: number;
  fatigue_top_fingerprints: Array<{ fingerprint: string; count: number }>;
  action_conversion_rate?: number | null;
  helpful_rate?: number | null;
  usefulness_score?: number | null;
  repeated_dismissals?: number;
  feedback_trend?: string;
};

export type TodaysFocusResponse = {
  generated_at: string;
  headline: string;
  requires_attention_today: string[];
  can_wait: string[];
  dangerous: string[];
  highest_upside: string[];
  top_actions: Array<{ recommendation_id?: string; action: string; tier: string }>;
  critical_alerts: Array<{ title: string; tier: string; why?: string }>;
  quick_wins: Array<{ title: string; action: string; effort: string }>;
  priority_queue: Array<{
    recommendation_id: string;
    title: string;
    summary: string;
    recommendation_score: number;
    priority_tier: string;
    priority_score?: number | null;
    seller_usefulness?: Record<string, unknown>;
  }>;
  advisory_notice: string;
};

export type ConversationReplyResponse = {
  question: string;
  answer: string;
  sources: string[];
  advisory_only: boolean;
};

export type DomainInsightView = {
  insight_id: string;
  analyst_id: string;
  analyst_label: string;
  statement: string;
  confidence: string | number;
  severity: string;
  priority_rank: number;
  evidence_refs?: string[];
  recommended_actions?: string[];
  business_impact_score?: string | number;
  reasoning_summary?: string;
};

export type ExplainabilityResponse = {
  summary_for_operator: string;
  confidence_rationale: string;
  evidence_graph: { nodes: unknown[]; edges: unknown[] };
  reasoning_trace: {
    steps: unknown[];
    domain_insights?: DomainInsightView[];
    multi_layer?: Record<string, unknown>;
  };
  provenance: Record<string, unknown>;
  freshness_score: string | number;
  trust_context?: {
    confidence_explanation?: string;
    limitations?: string[];
    urgency?: string;
    stale_data_note?: string | null;
    advisory_only?: boolean;
    seller_workflow_state?: string;
  };
};

export type AIOperationalStatusResponse = Record<string, unknown>;

export type IntelligenceRunCreateRequest = {
  workflow: string;
  prompt_id: string;
  semantics_version?: string;
  session_id?: string | null;
  report_id?: string | null;
};

export type IntelligenceRunResponse = {
  run_id: string;
  insight_id?: string | null;
  recommendation_id?: string | null;
  recommendation?: Record<string, unknown> | null;
  explainability?: ExplainabilityResponse | null;
  confidence: string | number;
  requires_human_approval: boolean;
  summary: string;
};

export type RecommendationFeedbackRequest = {
  rating?: number | null;
  helpful?: boolean | null;
  override_reason?: string | null;
  feedback_type?: string | null;
};


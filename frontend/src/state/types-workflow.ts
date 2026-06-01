export type WorkflowEventCreateRequest = {
  recommendation_id?: string | null;
  event_type: string;
  note?: string | null;
  reminder_at?: string | null;
  metadata_json?: Record<string, unknown> | null;
};

export type WorkflowEventResponse = {
  id: string;
  recommendation_id?: string | null;
  event_type: string;
  note?: string | null;
  reminder_at?: string | null;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
};

export type WorkflowHistoryResponse = {
  recommendation_id?: string | null;
  items: WorkflowEventResponse[];
};


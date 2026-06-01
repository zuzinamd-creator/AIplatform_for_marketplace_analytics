export type PageMeta = {
  total: number;
  skip: number;
  limit: number;
};

export type PaginatedQueueResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
  status_counts?: Record<string, number>;
};

export type PaginatedRebuildsResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
};

export type PaginatedAnomaliesResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
};

export type PaginatedDriftChecksResponse = {
  items: Array<Record<string, unknown>>;
  page: PageMeta;
};

export type RuntimeHealthResponse = Record<string, unknown>;
export type RuntimeSummaryResponse = Record<string, unknown>;

export type SemanticsStatusOpsResponse = {
  versions: Array<Record<string, unknown>>;
};


export type ReportResponse = {
  id: string;
  user_id: string;
  marketplace: string;
  report_type: string;
  original_filename: string;
  file_checksum: string;
  status: string;
  error_message?: string | null;
  created_at: string;
  processed_at?: string | null;
  job?: {
    id: string;
    status: string;
    attempts: number;
    last_error?: string | null;
    claimed_at?: string | null;
    completed_at?: string | null;
  } | null;
};

export type ReportUploadResponse = {
  report: ReportResponse;
  message: string;
};


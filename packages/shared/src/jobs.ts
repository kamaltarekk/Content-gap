// Shared job/queue names for pg-boss (API enqueues, worker consumes).
export const QUEUE_ANALYZE = "cgi.analyze";
export const QUEUE_WEEKLY_REFRESH = "cgi.weekly-refresh";

export interface AnalyzeJob {
  projectId: string;
  triggerType: "INGESTION" | "WEEKLY_REFRESH" | "MANUAL_SETUP" | "TEST";
}

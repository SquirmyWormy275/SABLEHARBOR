import type { SourcePin } from "./meetingSources";
import { request } from "./api";
export type BackgroundJob = {
  id: string;
  status:
    | "PENDING"
    | "RUNNING"
    | "COMPLETED"
    | "FAILED"
    | "CONFLICTED"
    | "INTERRUPTED";
  job_revision: number;
  expected_revision: number;
  attempts: number;
  created_at: string;
  updated_at: string;
  result_revision: number | null;
  error_code: string | null;
  error_message: string | null;
};
export function jobAction(job: BackgroundJob): "start" | "retry" | null {
  if (job.status === "PENDING") return "start";
  if (job.status === "FAILED" || job.status === "INTERRUPTED") return "retry";
  return null;
}
export function jobsPath(engagement: string) {
  return `/api/engagements/${encodeURIComponent(engagement)}/jobs`;
}
/** Caller supplies its existing command ID; retries must reuse this envelope unchanged. */
export function submitMeetingJob(
  engagement: string,
  command: {
    command_id: string;
    expected_revision: number;
    kind: "meeting.message";
    payload: {
      meeting_id: string;
      content: string;
      source_records?: SourcePin[];
    };
  },
) {
  return request<BackgroundJob>(jobsPath(engagement), "POST", command);
}

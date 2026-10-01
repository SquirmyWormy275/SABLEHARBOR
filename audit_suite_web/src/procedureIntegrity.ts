import type { Engagement } from "./api";

export type OriginalIntegrity = {
  schema_version: string;
  engagement_id: string;
  engagement_revision: number;
  status: string;
  metadata_status: string;
  automatic_testing_credit: false;
  counts: {
    referenced: number;
    verified: number;
    missing: number;
    integrity_failure: number;
    read_unavailable: number;
  } | null;
  artifacts: { artifact_id: string; status: string }[];
  traces: { id: string; status: string; artifact_ids?: string[] }[];
};

export function currentIntegrity(
  report: OriginalIntegrity,
  engagement: Engagement,
): boolean {
  return (
    report.schema_version === "1.0" &&
    report.engagement_id === engagement.id &&
    report.engagement_revision === engagement.revision &&
    report.automatic_testing_credit === false &&
    Array.isArray(report.artifacts) &&
    Array.isArray(report.traces)
  );
}

export function traceIntegrity(
  report: OriginalIntegrity | undefined,
  id: string,
) {
  if (!report) return null;
  const rows = report.traces.filter((row) => row.id === id);
  return rows.length === 1 ? rows[0] : null;
}

export const integrityStatusLabels: Record<string, string> = {
  VERIFIED_RETAINED_BYTES_ONLY:
    "Cited retained bytes match their recorded size and hash.",
  VERIFIED_RETAINED_BYTES: "Retained bytes match the recorded size and hash.",
  PARTIAL_UNAVAILABLE:
    "At least one cited copy or trace could not be verified.",
  NO_RECORDED_TRACES: "No procedure trace is recorded.",
  NO_RETAINED_ORIGINAL_REFERENCED:
    "The recorded trace cites no retained original.",
  METADATA_UNAVAILABLE: "Trace metadata or correction lineage is unavailable.",
  RECHECK_INPUT_UNAVAILABLE:
    "The bounded recheck could not run; no byte result is accepted.",
  NOT_RECHECKED: "This trace was not rechecked.",
  RETAINED_BYTES_UNAVAILABLE:
    "One or more cited retained copies could not be verified.",
  MISSING_RETAINED_BYTES: "The cited retained copy is missing.",
  RETAINED_BYTE_INTEGRITY_FAILURE:
    "The cited retained copy differs in size or hash.",
  RETAINED_BYTE_READ_UNAVAILABLE: "The cited retained copy could not be read.",
};

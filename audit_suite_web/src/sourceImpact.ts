import type { Engagement, Row } from "./api";
export type ImpactReport = {
  engagement_id: string;
  engagement_revision: number;
  changes: Row[];
  unavailable_comparisons: number;
  compared_artifacts: number;
  simulated_as_of: string;
  snapshot_isolation: string;
  limitations: string[];
  started_at: string;
  completed_at: string;
};
export function impactContext(e: Engagement): string {
  return JSON.stringify([
    e.id,
    e.revision,
    e.scope,
    e.permissions,
    e.company_source_binding,
    e.evidence_acquisition,
    e.simulated_at,
  ]);
}
export function validateImpact(
  value: ImpactReport,
  e: Engagement,
): ImpactReport {
  if (
    value.engagement_id !== e.id ||
    value.engagement_revision !== e.revision ||
    value.simulated_as_of !== e.simulated_at
  )
    throw Error(
      "Source comparison is outdated or belongs to another engagement. Check again.",
    );
  if (
    !Array.isArray(value.changes) ||
    !Number.isSafeInteger(value.compared_artifacts) ||
    value.compared_artifacts < 0 ||
    !Number.isSafeInteger(value.unavailable_comparisons) ||
    value.unavailable_comparisons < 0 ||
    value.changes.length > value.compared_artifacts
  )
    throw Error("Source comparison counts are invalid.");
  if (
    value.changes.some(
      (r) =>
        !e.artifacts.some((a) => a.id === r.artifact_id) ||
        !Array.isArray(r.references),
    )
  )
    throw Error("Source comparison references are outside this workspace.");
  return value;
}

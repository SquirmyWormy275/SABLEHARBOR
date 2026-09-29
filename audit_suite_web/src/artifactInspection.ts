import type { Engagement, Row } from "./api";
export function inspectionArtifact(e: Engagement, id: string): Row | undefined {
  const matches = e.artifacts.filter((a) => a.id === id);
  const a = matches[0];
  return matches.length === 1 &&
    a.status === "AVAILABLE" &&
    (a.audience ?? "LEARNER") === "LEARNER" &&
    typeof a.sha256 === "string" &&
    /^[a-f0-9]{64}$/.test(a.sha256) &&
    (a.version == null ||
      (Number.isSafeInteger(a.version) && Number(a.version) >= 0))
    ? a
    : undefined;
}
export function inspectionPins(a: Row) {
  return { artifact_id: a.id, sha256: a.sha256, version: a.version ?? null };
}
export function inspectionSubmission(values: Record<string, unknown>) {
  const payload = { ...values };
  if (payload.task_id === "" || payload.task_id == null) delete payload.task_id;
  return payload;
}
export function recordedInspections(e: Engagement, artifact: Row): Row[] {
  return (
    Array.isArray(e.artifact_inspections)
      ? (e.artifact_inspections as Row[])
      : []
  ).filter(
    (row) =>
      row.artifact_id === artifact.id &&
      row.sha256 === artifact.sha256 &&
      row.version === (artifact.version ?? null) &&
      row.classification === "SELF_REPORTED_INSPECTION",
  );
}

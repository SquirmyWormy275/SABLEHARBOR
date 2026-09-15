import type { Engagement, Row } from "./api";
import { record } from "./workpaperSupport";

export type EvidenceContextReference = {
  collection: "requests" | "controls" | "tasks" | "workpapers";
  id: string;
  version?: number;
};
export type EvidenceDraftSelection = { artifactId: string; controlId?: string };
const strings = (value: unknown): string[] =>
  Array.isArray(value)
    ? [
        ...new Set(
          value.filter((v): v is string => typeof v === "string" && !!v),
        ),
      ]
    : [];
const unique = (rows: Row[], id: string) => {
  const matches = rows.filter((row) => row.id === id);
  return matches.length === 1 ? matches[0] : undefined;
};
export function evidenceContextKey(
  e: Engagement,
  viewerId: string,
  artifactId: string,
) {
  const a = unique(e.artifacts, artifactId);
  return JSON.stringify([
    viewerId,
    e.id,
    e.revision,
    e.permissions,
    e.scope,
    e.company_source_binding,
    e.evidence_acquisition,
    e.simulated_at,
    artifactId,
    a?.sha256,
    a?.status,
  ]);
}
export function recordedEvidenceContext(e: Engagement, artifactId: string) {
  const artifact = unique(e.artifacts, artifactId);
  if (!artifact || artifact.status !== "AVAILABLE") return null;
  const requestId =
    typeof artifact.request_id === "string" ? artifact.request_id : "";
  const request = unique(e.requests, requestId);
  const native = record(record(record(artifact.source).receipt).source);
  const declaredIds = strings(record(native.provenance).control_ids);
  const declaredControls = declaredIds.flatMap((id) => {
    const control = unique(e.controls, id);
    return control ? [control] : [];
  });
  const requestedControl =
    typeof request?.control_id === "string"
      ? unique(e.controls, request.control_id)
      : undefined;
  const controlIds = new Set([
    ...declaredControls.map((c) => c.id),
    ...(requestedControl ? [requestedControl.id] : []),
  ]);
  const procedures = e.tasks.filter(
    (task) =>
      !!unique(e.tasks, task.id) &&
      controlIds.has(String(task.control_id)) &&
      (!task.boundary_id ||
        e.scope.boundaries.includes(String(task.boundary_id))) &&
      task.applicability !== "PRIOR_SCOPE_REQUIRES_REASSESSMENT" &&
      task.applicability !== "EXCLUDED" &&
      task.status !== "EXCLUDED",
  );
  const citations = e.workpapers.flatMap((paper) => {
    if (!Array.isArray(paper.versions) || !unique(e.workpapers, paper.id))
      return [];
    const versions = paper.versions;
    return versions.flatMap((value) => {
      const version = record(value);
      if (
        typeof version.version !== "number" ||
        !Number.isInteger(version.version) ||
        version.version < 1 ||
        versions.filter((v: unknown) => record(v).version === version.version)
          .length !== 1 ||
        !(
          strings(version.evidence_ids).includes(artifact.id) ||
          version.artifact_id === artifact.id
        )
      )
        return [];
      return [
        {
          paper,
          version: version.version,
          taskIds: strings(version.task_ids).filter(
            (id) => !!unique(e.tasks, id),
          ),
        },
      ];
    });
  });
  return {
    artifact,
    request,
    native,
    declaredControls,
    requestedControl,
    procedures,
    citations,
    declarationUnavailable: declaredIds.length !== declaredControls.length,
    canDraft: !!e.permissions?.some((p) => p === "learn" || p === "instruct"),
  };
}
/** Resolve a click against the current snapshot; no authority comes from caller-supplied roles. */
export function resolveEvidenceContextReference(
  e: Engagement,
  ref: EvidenceContextReference,
): Row | undefined {
  const row = unique(e[ref.collection], ref.id);
  if (!row) return undefined;
  if (ref.collection === "workpapers") {
    if (
      !Array.isArray(row.versions) ||
      typeof ref.version !== "number" ||
      row.versions.filter((v) => record(v).version === ref.version).length !== 1
    )
      return undefined;
  } else if (ref.version !== undefined) return undefined;
  return row;
}

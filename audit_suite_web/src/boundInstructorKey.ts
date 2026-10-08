import type { Scope } from "./api";
import {
  validateReferenceCrosswalk,
  type ReferenceCrosswalkValue,
} from "./referenceCrosswalk";
export type BoundSource = {
  id: string;
  company: string;
  branch: string;
  system: string;
  record: string;
  version: number;
  sha256: string;
  source_store_id?: string;
  source_system_alias?: string;
  registry_sha256?: string;
  event_at: string | null;
  available_at: string;
  imported_at: string;
  actor_granted_at_binding: boolean;
  actor_visibility_at_binding:
    | "FUTURE_UNAVAILABLE"
    | "ACCESS_NOT_GRANTED"
    | "DISCOVERABLE_LATEST"
    | "READABLE_PRIOR_VERSION";
  retained_audit_artifact_ids: string[];
  fact_verification: string;
};
export type BoundIssue = {
  id: string;
  control_ids: string[];
  source_ids: string[];
  claim: string;
  uncertainty: string;
};
export type BoundExpectation = {
  id: string;
  issue_ids: string[];
  procedure: string;
  acceptable_alternatives: string[];
  task_ids?: string[];
};
export type BoundSnapshot = {
  snapshot_isolation?: "PER_COMPONENT_NOT_GLOBAL";
  status: "BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED";
  created_at: string;
  audited_actor_id: string;
  operator_source_as_of: string;
  engagement: {
    id: string;
    revision: number;
    scope: Scope;
    simulated_at: string;
    state_sha256: string;
    history_sha256: string;
  };
  sources: BoundSource[];
  authored: {
    issues: BoundIssue[];
    expectations: BoundExpectation[];
    uncertainty: string[];
    source_pins: Record<string, string>;
  };
  software_verified: string[];
  professional_validation: "UNVALIDATED";
  authored_status: "INSTRUCTOR_AUTHORED_INFERENCE";
  grading: "NOT_PERFORMED";
  limits: string[];
};
export type BoundResponse = {
  reference_crosswalk?: ReferenceCrosswalkValue;
  snapshot: BoundSnapshot;
  binding: {
    manifest_sha256: string;
    engagement_id: string;
    bound_revision: number;
    current_revision: number;
    status: "MATCHING_REVISION" | "HISTORICAL_REVISION";
  };
};
export function validateBoundResponse(v: BoundResponse, engagementId: string) {
  if (v.reference_crosswalk)
    validateReferenceCrosswalk(v.reference_crosswalk, engagementId);
  const s = v.snapshot,
    b = v.binding;
  if (
    v.reference_crosswalk &&
    (JSON.stringify(v.reference_crosswalk.current_cards.map((c) => c.id)) !==
      JSON.stringify(s.authored.issues.map((i) => i.id)) ||
      v.reference_crosswalk.current_cards.some(
        (c, index) =>
          JSON.stringify(c.control_ids) !==
          JSON.stringify(s.authored.issues[index].control_ids),
      ))
  )
    throw Error(
      "Reference crosswalk current cards differ from this bound snapshot.",
    );
  if (
    !s ||
    !b ||
    s.status !== "BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED" ||
    s.professional_validation !== "UNVALIDATED" ||
    s.grading !== "NOT_PERFORMED" ||
    s.authored_status !== "INSTRUCTOR_AUTHORED_INFERENCE" ||
    s.engagement.id !== engagementId ||
    b.engagement_id !== engagementId ||
    s.engagement.revision !== b.bound_revision ||
    !/^[a-f0-9]{64}$/.test(b.manifest_sha256)
  )
    throw Error("Protected explanation binding is inconsistent.");
  if (
    b.status !==
    (b.current_revision === b.bound_revision
      ? "MATCHING_REVISION"
      : "HISTORICAL_REVISION")
  )
    throw Error("Historical revision status is inconsistent.");
  const sourceIds = new Set(s.sources.map((x) => x.id)),
    issueIds = new Set(s.authored.issues.map((x) => x.id));
  if (
    sourceIds.size !== s.sources.length ||
    issueIds.size !== s.authored.issues.length ||
    s.authored.issues.some((i) =>
      i.source_ids.some((id) => !sourceIds.has(id)),
    ) ||
    s.authored.expectations.some((e) =>
      e.issue_ids.some((id) => !issueIds.has(id)),
    )
  )
    throw Error("Authored references do not match the retained source graph.");
  if (
    s.sources.some((source) => {
      const routed =
        s.snapshot_isolation === "PER_COMPONENT_NOT_GLOBAL" ||
        [
          source.source_store_id,
          source.source_system_alias,
          source.registry_sha256,
        ].some((value) => value !== undefined);
      return (
        routed &&
        (typeof source.source_store_id !== "string" ||
          !source.source_store_id ||
          typeof source.source_system_alias !== "string" ||
          !source.source_system_alias ||
          typeof source.registry_sha256 !== "string" ||
          !/^[a-f0-9]{64}$/.test(source.registry_sha256))
      );
    })
  )
    throw Error("Protected source routing pins are incomplete.");
  if (
    s.authored.expectations.some(
      (expectation) =>
        expectation.task_ids !== undefined &&
        (!Array.isArray(expectation.task_ids) ||
          expectation.task_ids.some((id) => typeof id !== "string" || !id) ||
          new Set(expectation.task_ids).size !== expectation.task_ids.length),
    )
  )
    throw Error("Authored procedure links are invalid.");
}
export function sourceTimeline(sources: BoundSource[]) {
  return sources
    .flatMap((source) =>
      (["event_at", "available_at", "imported_at"] as const)
        .filter((field) => source[field] != null)
        .map((field) => ({
          sourceId: source.id,
          field,
          at: source[field]!,
          record: source.record,
        })),
    )
    .sort((a, b) => {
      const left = Date.parse(a.at),
        right = Date.parse(b.at);
      return (
        (Number.isFinite(left) ? left : Infinity) -
          (Number.isFinite(right) ? right : Infinity) ||
        a.sourceId.localeCompare(b.sourceId) ||
        a.field.localeCompare(b.field)
      );
    });
}
export function authoredRelationships(snapshot: BoundSnapshot) {
  return [
    ...snapshot.authored.issues.flatMap((issue) =>
      issue.source_ids.map((id) => ({
        from: issue.id,
        to: id,
        relation: "AUTHORED_SOURCE_REFERENCE" as const,
      })),
    ),
    ...snapshot.authored.expectations.flatMap((expectation) =>
      expectation.issue_ids.map((id) => ({
        from: expectation.id,
        to: id,
        relation: "AUTHORED_EXPECTATION_REFERENCE" as const,
      })),
    ),
  ];
}
